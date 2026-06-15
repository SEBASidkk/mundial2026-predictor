"""Betting pick enumeration, odds attachment and ranking.

A "pick" is one selection of one market for one match, carrying:
  - the model's probability it hits,
  - a decimal odd (real bookmaker odd when available, else fair = 1/prob),
  - whether the odd is real ("market") or derived ("fair"),
  - the implied probability of that odd and the value edge vs the model.

Best bets = picks ranked by model probability (most likely to hit first).
"""
from __future__ import annotations

from typing import Dict, List, Optional
from sqlalchemy.orm import Session, joinedload

from app.models.match import Match
from app.models.prediction import Prediction
from app.models.odds import Odds
from pipeline.models.markets import compute_all_markets

# Trivial near-locks and extreme longshots add little signal; keep picks in a
# sensible band so "best bets" stays informative.
MIN_PROB = 0.50
MAX_PROB = 0.97


def _fair_odds(prob: float) -> float:
    return round(1.0 / prob, 2) if prob > 0 else 0.0


def _markets_for(pred: Prediction) -> Dict:
    return compute_all_markets({
        "prob_home_win": pred.prob_home_win,
        "prob_draw": pred.prob_draw,
        "prob_away_win": pred.prob_away_win,
        "lambda_home": pred.lambda_home,
        "lambda_away": pred.lambda_away,
        "score_matrix": pred.score_matrix or {},
    })


def _candidate_selections(markets: Dict, home: str, away: str) -> List[Dict]:
    """Flat list of (market, selection, label, prob) candidates for a match."""
    r = markets["result_1x2"]
    btts = markets["btts"]
    return [
        {"market": "1x2", "selection": "home", "label": f"Gana {home}", "prob": r["home"]},
        {"market": "1x2", "selection": "draw", "label": "Empate", "prob": r["draw"]},
        {"market": "1x2", "selection": "away", "label": f"Gana {away}", "prob": r["away"]},
        {"market": "over_05", "selection": "over", "label": "Over 0.5 goles", "prob": markets["over_05"]},
        {"market": "over_15", "selection": "over", "label": "Over 1.5 goles", "prob": markets["over_15"]},
        {"market": "over_25", "selection": "over", "label": "Over 2.5 goles", "prob": markets["over_25"]},
        {"market": "over_35", "selection": "over", "label": "Over 3.5 goles", "prob": markets["over_35"]},
        {"market": "under_25", "selection": "under", "label": "Under 2.5 goles", "prob": markets["under_25"]},
        {"market": "btts", "selection": "yes", "label": "Ambos anotan", "prob": btts},
        {"market": "btts", "selection": "no", "label": "No ambos anotan", "prob": 1.0 - btts},
    ]


def build_match_picks(
    match: Match,
    odds_index: Optional[Dict] = None,
    apply_band: bool = True,
) -> List[Dict]:
    """Picks for one match, sorted by model probability descending.

    odds_index: {(match_id, market, selection): Odds} for real-odds lookup.
    """
    if match.prediction is None:
        return []
    odds_index = odds_index or {}
    markets = _markets_for(match.prediction)
    home = match.home_team.name
    away = match.away_team.name

    picks: List[Dict] = []
    for c in _candidate_selections(markets, home, away):
        prob = round(c["prob"], 5)
        if apply_band and not (MIN_PROB <= prob <= MAX_PROB):
            continue
        real = odds_index.get((match.id, c["market"], c["selection"]))
        if real is not None:
            decimal_odds = round(real.decimal_odds, 2)
            source = "market"
            bookmaker = real.bookmaker
        else:
            decimal_odds = _fair_odds(prob)
            source = "fair"
            bookmaker = None
        implied = round(1.0 / decimal_odds, 5) if decimal_odds > 0 else 0.0
        picks.append({
            "match_id": match.id,
            "home_team": home,
            "away_team": away,
            "kickoff_utc": match.kickoff_utc.isoformat(),
            "market": c["market"],
            "selection": c["selection"],
            "label": c["label"],
            "model_prob": prob,
            "decimal_odds": decimal_odds,
            "implied_prob": implied,
            "edge": round(prob - implied, 5),   # >0 => model sees value
            "source": source,
            "bookmaker": bookmaker,
        })
    picks.sort(key=lambda p: p["model_prob"], reverse=True)
    return picks


def _odds_index(db: Session, match_ids: List[int]) -> Dict:
    if not match_ids:
        return {}
    rows = db.query(Odds).filter(Odds.match_id.in_(match_ids)).all()
    return {(o.match_id, o.market, o.selection): o for o in rows}


def best_bets(db: Session, limit: int = 20, per_match: int = 1) -> List[Dict]:
    """Top picks across all upcoming matches, ranked by model probability.

    Takes the strongest `per_match` picks from each match (default 1) so the
    leaderboard spans many fixtures instead of repeating the same near-lock
    market (e.g. Over 0.5) for every game.
    """
    matches = (
        db.query(Match)
        .options(
            joinedload(Match.home_team),
            joinedload(Match.away_team),
            joinedload(Match.prediction),
        )
        .filter(Match.played == False)  # noqa: E712
        .all()
    )
    idx = _odds_index(db, [m.id for m in matches])
    # Over 0.5 / 1.5 are near-certain in almost every match — they'd flood the
    # board with identical rows. Keep them in per-match detail, drop them here.
    trivial = {"over_05", "over_15"}
    all_picks: List[Dict] = []
    for m in matches:
        meaningful = [p for p in build_match_picks(m, idx) if p["market"] not in trivial]
        all_picks.extend(meaningful[:per_match])
    all_picks.sort(key=lambda p: p["model_prob"], reverse=True)
    return all_picks[:limit]


def match_picks(db: Session, match: Match) -> List[Dict]:
    """Picks for a single match (used in the match detail view)."""
    idx = _odds_index(db, [match.id])
    return build_match_picks(match, idx)
