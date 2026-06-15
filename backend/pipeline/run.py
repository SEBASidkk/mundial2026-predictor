"""
Full pipeline orchestrator.
Usage: python -m pipeline.run
"""
import math
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.team import Team
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.odds import Odds
from pipeline.ingestion.football_data import (
    fetch_world_cup_teams,
    fetch_world_cup_matches,
    fetch_historical_matches,
)
from pipeline.ingestion.odds_api import fetch_odds, map_events_to_matches
from pipeline.features.elo import compute_elo_ratings
from pipeline.features.seed_ratings import seed_team_elos, strengths_from_elo
from pipeline.features.calibration import (
    updated_elos,
    compute_goal_calibration,
    team_base_lambdas,
)
from pipeline.models.dixon_coles import fit_dixon_coles, predict_match
from pipeline.models.ensemble import blend_predictions, compute_confidence, elo_to_prob

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)


def upsert_teams(db: Session, teams_data: list):
    for t in teams_data:
        existing = db.query(Team).filter_by(external_id=t["external_id"]).first()
        if existing:
            existing.name = t["name"]
            existing.short_name = t.get("short_name")
            existing.country_code = t.get("country_code")
        else:
            db.add(Team(**t, elo_rating=1500.0))
    db.commit()
    log.info(f"Upserted {len(teams_data)} teams")


def upsert_matches(db: Session, matches_data: list):
    team_map = {t.external_id: t.id for t in db.query(Team).all()}
    for m in matches_data:
        h_id = team_map.get(m["home_external_id"])
        a_id = team_map.get(m["away_external_id"])
        if not h_id or not a_id:
            continue
        existing = db.query(Match).filter_by(external_id=m["external_id"]).first()
        played = m["status"] == "FINISHED"
        if existing:
            existing.home_goals = m.get("home_goals")
            existing.away_goals = m.get("away_goals")
            existing.played = played
        else:
            db.add(Match(
                external_id=m["external_id"],
                home_team_id=h_id,
                away_team_id=a_id,
                kickoff_utc=datetime.fromisoformat(m["kickoff_utc"].replace("Z", "+00:00")),
                stage=m.get("stage"),
                group=m.get("group"),
                venue_city=m.get("venue"),
                played=played,
                home_goals=m.get("home_goals"),
                away_goals=m.get("away_goals"),
            ))
    db.commit()
    log.info(f"Upserted {len(matches_data)} matches")


def upsert_odds(db: Session):
    """Fetch real odds and replace the Odds table. No-op (cleared) without a key."""
    matches = (
        db.query(Match)
        .filter(Match.played == False)  # noqa: E712
        .all()
    )
    events = fetch_odds()
    rows = map_events_to_matches(events, matches) if events else []
    # Fresh snapshot each run: clear and reinsert.
    db.query(Odds).delete()
    for r in rows:
        db.add(Odds(**r))
    db.commit()
    log.info(f"Upserted {len(rows)} odds rows")


def run_predictions(db: Session, dc_params: dict, elo_ratings: dict,
                    calibration: dict = None):
    calibration = calibration or {"off_home": 0.0, "off_away": 0.0}
    c_home = math.exp(calibration.get("off_home", 0.0))
    c_away = math.exp(calibration.get("off_away", 0.0))

    upcoming = db.query(Match).filter(Match.played == False).all()
    for match in upcoming:
        home_team = db.query(Team).filter_by(id=match.home_team_id).first()
        away_team = db.query(Team).filter_by(id=match.away_team_id).first()
        if not home_team or not away_team:
            continue

        h_ext = home_team.external_id
        a_ext = away_team.external_id

        # Base goal rates (fitted Dixon-Coles when available, else ELO strengths)
        # then apply the recency goal-level calibration so the global scoring
        # level tracks what teams are actually scoring this tournament.
        lambda_home, lambda_away = team_base_lambdas(
            home_team.elo_rating, away_team.elo_rating, dc_params, h_ext, a_ext
        )
        lambda_home *= c_home
        lambda_away *= c_away

        dc_result = predict_match(lambda_home, lambda_away, rho=dc_params["rho"])

        elo_diff = (
            elo_ratings.get(h_ext, home_team.elo_rating)
            - elo_ratings.get(a_ext, away_team.elo_rating)
        )
        # Second, genuinely independent model: an ELO-logistic 1x2 (vs the
        # score-based Dixon-Coles). Their disagreement drives model_confidence,
        # which previously collapsed to 1.0 because this slot just copied DC.
        e_home = elo_to_prob(elo_diff)
        draw_base = 0.24
        xgb_result = {
            "prob_home_win": e_home * (1 - draw_base),
            "prob_draw": draw_base,
            "prob_away_win": (1 - e_home) * (1 - draw_base),
        }
        blended = blend_predictions(dc_result, xgb_result, elo_diff)
        confidence = compute_confidence(dc_result, xgb_result)

        existing_pred = db.query(Prediction).filter_by(match_id=match.id).first()
        if existing_pred:
            existing_pred.prob_home_win = blended["prob_home_win"]
            existing_pred.prob_draw = blended["prob_draw"]
            existing_pred.prob_away_win = blended["prob_away_win"]
            existing_pred.lambda_home = lambda_home
            existing_pred.lambda_away = lambda_away
            existing_pred.score_matrix = dc_result["score_matrix"]
            existing_pred.model_confidence = confidence
            existing_pred.generated_at = datetime.utcnow()
        else:
            db.add(Prediction(
                match_id=match.id,
                prob_home_win=blended["prob_home_win"],
                prob_draw=blended["prob_draw"],
                prob_away_win=blended["prob_away_win"],
                lambda_home=lambda_home,
                lambda_away=lambda_away,
                score_matrix=dc_result["score_matrix"],
                model_confidence=confidence,
            ))
    db.commit()
    log.info(f"Generated predictions for {len(upcoming)} matches")


def run():
    db = SessionLocal()
    try:
        log.info("Starting pipeline run...")

        teams_data = fetch_world_cup_teams()
        upsert_teams(db, teams_data)

        matches_data = fetch_world_cup_matches()
        upsert_matches(db, matches_data)

        historical = fetch_historical_matches(seasons=[2018, 2022])

        # No historical results from the free API tier → seed approximate ELOs so
        # teams (and therefore predictions) are differentiated instead of uniform.
        if not historical:
            n = seed_team_elos(db)
            log.info(f"No historical data — seeded {n} team ELO ratings")

        dc_params = fit_dixon_coles(historical) if historical else {
            "attack": {}, "defense": {}, "home_advantage": 0.3, "rho": -0.1,
        }

        # Recency: re-rate teams from this tournament's real results, persist.
        elo_ratings = updated_elos(db)
        for t in db.query(Team).all():
            if t.id in elo_ratings:
                t.elo_rating = elo_ratings[t.id]
        db.commit()

        # Calibrate the global goal level against actual scorelines (kills the
        # Under bias when the prior under-predicts goals).
        calibration = compute_goal_calibration(db, dc_params)
        log.info(
            f"Goal calibration from {calibration['n']} played matches: "
            f"home x{math.exp(calibration['off_home']):.3f}, "
            f"away x{math.exp(calibration['off_away']):.3f}"
        )

        run_predictions(db, dc_params, elo_ratings, calibration)
        upsert_odds(db)
        log.info("Pipeline complete.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
