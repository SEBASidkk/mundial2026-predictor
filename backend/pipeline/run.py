"""
Full pipeline orchestrator.
Usage: python -m pipeline.run
"""
import math
import logging
from datetime import datetime, timezone
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
from pipeline.ingestion.historical import load_matches
from pipeline.features.elo import compute_elo_ratings
from pipeline.features.historical_elo import run_elo, recent_form
from pipeline.features.seed_ratings import (
    seed_team_elos, strengths_from_elo, host_advantages, HOST_TEAMS, SEED_ELO, DEFAULT_ELO,
)
from pipeline.features.dc_fit import fit_from_history, save_dc_params
from pipeline.features.calibration import (
    updated_elos,
    compute_goal_calibration,
    team_base_lambdas,
)
from pipeline.models.dixon_coles import fit_dixon_coles, predict_match
from pipeline.models.goals_gbm import (
    train_and_save as train_gbm, evaluate_holdout, save_holdout, GoalsGBM,
)
from pipeline.models.ensemble import (
    blend_predictions,
    compute_confidence,
    elo_to_prob,
    fit_ensemble_weights,
    save_weights,
    second_opinion_1x2,
    DEFAULT_WEIGHTS,
)

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


def build_weight_samples(db: Session, dc_params: dict, calibration: dict,
                         gbm=None, forms=None):
    """(dc_probs, xgb_probs, elo_diff, outcome) tuples from played matches,
    used to learn the ensemble weights."""
    c_home = math.exp(calibration.get("off_home", 0.0))
    c_away = math.exp(calibration.get("off_away", 0.0))
    teams = {t.id: t for t in db.query(Team).all()}
    samples = []
    from pipeline.features.calibration import played_matches, team_base_lambdas
    for m in played_matches(db):
        h = teams.get(m["home_id"])
        a = teams.get(m["away_id"])
        if h is None or a is None:
            continue
        hadv, aadv = host_advantages(h.name, a.name)
        lam_h, lam_a = team_base_lambdas(
            h.elo_rating, a.elo_rating, dc_params, h.external_id, a.external_id,
            home_adv=hadv, away_adv=aadv,
        )
        lam_h *= c_home
        lam_a *= c_away
        dc = predict_match(lam_h, lam_a, rho=dc_params.get("rho", -0.1))
        elo_diff = h.elo_rating - a.elo_rating
        xgb = second_opinion_1x2(gbm, forms, h.name, a.name, h.elo_rating, a.elo_rating)
        hg, ag = m["home_goals"], m["away_goals"]
        outcome = 0 if hg > ag else (1 if hg == ag else 2)
        samples.append((dc, xgb, elo_diff, outcome))
    return samples


def run_predictions(db: Session, dc_params: dict, elo_ratings: dict,
                    calibration: dict = None, weights=None, gbm=None, forms=None):
    calibration = calibration or {"off_home": 0.0, "off_away": 0.0}
    weights = weights or DEFAULT_WEIGHTS
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
        # with a host-only home edge (neutral venues get none), then the recency
        # goal-level calibration so the global scoring level tracks reality.
        hadv, aadv = host_advantages(home_team.name, away_team.name)
        lambda_home, lambda_away = team_base_lambdas(
            home_team.elo_rating, away_team.elo_rating, dc_params, h_ext, a_ext,
            home_adv=hadv, away_adv=aadv,
        )
        lambda_home *= c_home
        lambda_away *= c_away

        dc_result = predict_match(lambda_home, lambda_away, rho=dc_params["rho"])

        elo_diff = (
            elo_ratings.get(h_ext, home_team.elo_rating)
            - elo_ratings.get(a_ext, away_team.elo_rating)
        )
        # Second, genuinely independent model: the trained Poisson-GBM (real ML
        # on real history) when available, else an ELO-logistic. Its disagreement
        # with Dixon-Coles drives model_confidence.
        xgb_result = second_opinion_1x2(
            gbm, forms, home_team.name, away_team.name,
            home_team.elo_rating, away_team.elo_rating,
        )
        blended = blend_predictions(dc_result, xgb_result, elo_diff, weights)
        confidence = compute_confidence(dc_result, xgb_result, blended)

        existing_pred = db.query(Prediction).filter_by(match_id=match.id).first()
        if existing_pred:
            existing_pred.prob_home_win = blended["prob_home_win"]
            existing_pred.prob_draw = blended["prob_draw"]
            existing_pred.prob_away_win = blended["prob_away_win"]
            existing_pred.lambda_home = lambda_home
            existing_pred.lambda_away = lambda_away
            existing_pred.score_matrix = dc_result["score_matrix"]
            existing_pred.model_confidence = confidence
            existing_pred.generated_at = datetime.now(timezone.utc)
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

        # Real history (martj42, ~49k matches). Drives data ELOs, the DC fit and
        # the gradient-boosted goals model. Falls back to seed ELOs if unavailable.
        history = load_matches()
        gbm: GoalsGBM | None = None
        forms = None

        if history:
            data_elos, feature_rows = run_elo(history)
            forms = recent_form(history)
            teams = db.query(Team).all()
            mapped = 0
            for t in teams:
                if t.name in data_elos:
                    t.elo_rating = data_elos[t.name]
                    mapped += 1
                else:
                    t.elo_rating = SEED_ELO.get(t.name, DEFAULT_ELO)
            db.commit()
            log.info("Data ELOs from %d historical matches (%d/%d WC teams mapped).",
                     len(history), mapped, len(teams))

            name_to_ext = {t.name: t.external_id for t in teams}
            dc_params = fit_from_history(history, set(name_to_ext), name_to_ext) or {
                "attack": {}, "defense": {}, "home_advantage": 0.3, "rho": -0.1,
            }
            save_dc_params(dc_params)
            gbm = train_gbm(feature_rows)
            holdout = evaluate_holdout(feature_rows)
            if holdout:
                save_holdout(holdout)
                log.info(
                    "GBM out-of-sample (%d matches): Brier %.3f (base %.3f), "
                    "acc %.1f%%, log-loss %.3f",
                    holdout["n"], holdout["brier"], holdout["baseline_brier"],
                    holdout["accuracy"] * 100, holdout["log_loss"],
                )
        else:
            n = seed_team_elos(db)
            log.info("No historical data — seeded %d team ELO ratings", n)
            dc_params = {"attack": {}, "defense": {}, "home_advantage": 0.3, "rho": -0.1}

        # elo_ratings dict left empty: team_base_lambdas / ELO terms read the
        # persisted Team.elo_rating (the data ELO) via fallback.
        elo_ratings: dict = {}

        # Calibrate the global goal level against actual scorelines.
        calibration = compute_goal_calibration(db, dc_params)
        log.info(
            f"Goal calibration from {calibration['n']} played matches: "
            f"x{math.exp(calibration['off_home']):.3f} (global)"
        )

        # Learn ensemble weights from played matches (shrunk toward defaults).
        samples = build_weight_samples(db, dc_params, calibration, gbm, forms)
        weights = fit_ensemble_weights(samples)
        save_weights(weights)
        log.info(
            "Ensemble weights (DC/GBM/ELO) from %d samples: %.3f / %.3f / %.3f",
            len(samples), *weights,
        )

        run_predictions(db, dc_params, elo_ratings, calibration, weights, gbm, forms)
        upsert_odds(db)
        log.info("Pipeline complete.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
