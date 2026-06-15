from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.database import get_db
from app.models.match import Match
from app.models.prediction import Prediction
from app.schemas.match import MatchOut, MatchDetailOut
from app.schemas.prediction import PredictionOut, MarketOut, ScoreEntry
from app.schemas.bets import BetPickOut
from app.services.bets import match_picks
from app.services.simulate import simulate_match
from pipeline.models.markets import compute_all_markets

router = APIRouter()


def _build_prediction_out(pred: Prediction) -> PredictionOut | None:
    if pred is None:
        return None
    markets_raw = compute_all_markets({
        "prob_home_win": pred.prob_home_win,
        "prob_draw": pred.prob_draw,
        "prob_away_win": pred.prob_away_win,
        "lambda_home": pred.lambda_home,
        "lambda_away": pred.lambda_away,
        "score_matrix": pred.score_matrix or {},
    })
    market_out = MarketOut(
        result_1x2=markets_raw["result_1x2"],
        over_05=markets_raw["over_05"],
        over_15=markets_raw["over_15"],
        over_25=markets_raw["over_25"],
        over_35=markets_raw["over_35"],
        over_45=markets_raw["over_45"],
        under_25=markets_raw["under_25"],
        btts=markets_raw["btts"],
        top_scores=[ScoreEntry(**s) for s in markets_raw["top_scores"]],
        model_confidence=pred.model_confidence or 0.0,
    )
    return PredictionOut(
        prob_home_win=pred.prob_home_win,
        prob_draw=pred.prob_draw,
        prob_away_win=pred.prob_away_win,
        lambda_home=pred.lambda_home,
        lambda_away=pred.lambda_away,
        markets=market_out,
        model_confidence=pred.model_confidence or 0.0,
        generated_at=pred.generated_at.isoformat(),
    )


@router.get("/matches", response_model=List[MatchOut])
def list_matches(db: Session = Depends(get_db)):
    matches = (
        db.query(Match)
        .options(
            joinedload(Match.home_team),
            joinedload(Match.away_team),
            joinedload(Match.prediction),
        )
        .order_by(Match.kickoff_utc)
        .all()
    )
    return [
        MatchOut(
            id=m.id,
            home_team=m.home_team,
            away_team=m.away_team,
            kickoff_utc=m.kickoff_utc,
            stage=m.stage,
            group=m.group,
            venue_city=m.venue_city,
            played=m.played,
            home_goals=m.home_goals,
            away_goals=m.away_goals,
            prediction=_build_prediction_out(m.prediction),
        )
        for m in matches
    ]


@router.get("/match/{match_id}", response_model=MatchDetailOut)
def get_match(match_id: int, db: Session = Depends(get_db)):
    match = (
        db.query(Match)
        .options(
            joinedload(Match.home_team),
            joinedload(Match.away_team),
            joinedload(Match.prediction),
        )
        .filter(Match.id == match_id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    bets = [BetPickOut(**p) for p in match_picks(db, match)] if not match.played else []
    return MatchDetailOut(
        id=match.id,
        home_team=match.home_team,
        away_team=match.away_team,
        kickoff_utc=match.kickoff_utc,
        stage=match.stage,
        group=match.group,
        venue_city=match.venue_city,
        played=match.played,
        home_goals=match.home_goals,
        away_goals=match.away_goals,
        prediction=_build_prediction_out(match.prediction),
        bets=bets,
    )


@router.get("/match/{match_id}/simulate")
def simulate(
    match_id: int,
    n: int = Query(10000, ge=100, le=100000),
    db: Session = Depends(get_db),
):
    match = (
        db.query(Match)
        .options(joinedload(Match.home_team), joinedload(Match.away_team), joinedload(Match.prediction))
        .filter(Match.id == match_id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return simulate_match(match, n=n)
