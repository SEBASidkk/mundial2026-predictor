"""Backtesting and calibration metrics over played matches.

Reconstructs the model's 1x2 prediction for every finished match (using the
same goal-rate path the live pipeline uses) and scores it against the real
result. Produces the numbers that tell us whether the model is actually any
good, instead of trusting it blind:

  * Brier score        — mean squared error of the probability vector (lower
                         is better; 0 = perfect, ~0.66 = uniform guess).
  * Log-loss           — penalises confident wrong calls harder than Brier.
  * Accuracy           — share of matches whose most-likely outcome happened.
  * Reliability curve  — predicted vs observed frequency in probability bins;
                         a well-calibrated model sits on the diagonal.
  * ROI                — flat-stake return betting the model's value picks at
                         the real bookmaker odds (None when no odds exist).

This is in-sample (it uses end-of-tournament ratings), so treat it as a
sanity/calibration check rather than a true out-of-sample edge estimate; the
reliability curve in particular still exposes systematic over/under-confidence.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.odds import Odds
from app.models.team import Team
from pipeline.features.calibration import team_base_lambdas, played_matches
from pipeline.models.dixon_coles import predict_match
from pipeline.models.ensemble import blend_predictions, load_weights, elo_to_prob, _elo_1x2

_KEYS = ("prob_home_win", "prob_draw", "prob_away_win")


def _outcome(home_goals: int, away_goals: int) -> int:
    if home_goals > away_goals:
        return 0
    if home_goals == away_goals:
        return 1
    return 2


def _reconstruct_prediction(
    home: Team, away: Team, dc_params: Dict, calibration: Dict,
    weights: Tuple[float, float, float],
) -> Dict[str, float]:
    """1x2 probabilities for a fixture via the live ensemble path."""
    from pipeline.features.seed_ratings import host_advantages

    c_home = math.exp(calibration.get("off_home", 0.0))
    c_away = math.exp(calibration.get("off_away", 0.0))
    hadv, aadv = host_advantages(home.name, away.name)
    lam_h, lam_a = team_base_lambdas(
        home.elo_rating, away.elo_rating, dc_params, home.external_id, away.external_id,
        home_adv=hadv, away_adv=aadv,
    )
    lam_h *= c_home
    lam_a *= c_away
    dc = predict_match(lam_h, lam_a, rho=dc_params.get("rho", -0.1))
    elo_diff = home.elo_rating - away.elo_rating
    xgb = _elo_1x2(elo_diff)
    return blend_predictions(dc, xgb, elo_diff, weights)


def reliability_bins(
    pairs: List[Tuple[float, int]], n_bins: int = 10
) -> List[Dict]:
    """Group (predicted_prob, hit) pairs into bins for a calibration curve."""
    bins: List[Dict] = []
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        chunk = [(p, h) for p, h in pairs if (lo <= p < hi or (b == n_bins - 1 and p == 1.0))]
        if not chunk:
            continue
        avg_pred = sum(p for p, _ in chunk) / len(chunk)
        observed = sum(h for _, h in chunk) / len(chunk)
        bins.append({
            "bin": f"{lo:.1f}-{hi:.1f}",
            "avg_predicted": round(avg_pred, 4),
            "observed_freq": round(observed, 4),
            "count": len(chunk),
        })
    return bins


def backtest(
    db: Session, dc_params: Optional[Dict] = None, calibration: Optional[Dict] = None,
) -> Dict:
    """Full metric bundle over every played match. Empty-safe."""
    dc_params = dc_params or {"attack": {}, "defense": {}, "home_advantage": 0.3, "rho": -0.1}
    calibration = calibration or {"off_home": 0.0, "off_away": 0.0}
    weights = load_weights()

    teams = {t.id: t for t in db.query(Team).all()}
    rows = (
        db.query(Match)
        .filter(Match.played == True)  # noqa: E712
        .filter(Match.home_goals.isnot(None))
        .order_by(Match.kickoff_utc.asc())
        .all()
    )
    odds_idx = {
        (o.match_id, o.market, o.selection): o
        for o in db.query(Odds).all()
    }

    brier_sum = 0.0
    logloss_sum = 0.0
    correct = 0
    rel_pairs: List[Tuple[float, int]] = []
    staked = 0.0
    returned = 0.0
    n = 0

    for m in rows:
        h, a = teams.get(m.home_team_id), teams.get(m.away_team_id)
        if h is None or a is None:
            continue
        probs = _reconstruct_prediction(h, a, dc_params, calibration, weights)
        outcome = _outcome(m.home_goals, m.away_goals)
        p_vec = [probs[k] for k in _KEYS]

        target = [1.0 if i == outcome else 0.0 for i in range(3)]
        brier_sum += sum((p - t) ** 2 for p, t in zip(p_vec, target))
        logloss_sum += -math.log(max(1e-9, p_vec[outcome]))
        pred_idx = max(range(3), key=lambda i: p_vec[i])
        if pred_idx == outcome:
            correct += 1
        rel_pairs.append((p_vec[pred_idx], 1 if pred_idx == outcome else 0))

        # Flat-stake ROI: back the value selection (model prob > implied) at real odds.
        sel_keys = [("1x2", "home"), ("1x2", "draw"), ("1x2", "away")]
        for i, (mk, sel) in enumerate(sel_keys):
            o = odds_idx.get((m.id, mk, sel))
            if o is None or o.decimal_odds <= 1.0:
                continue
            implied = 1.0 / o.decimal_odds
            if p_vec[i] > implied:  # model sees value
                staked += 1.0
                if i == outcome:
                    returned += o.decimal_odds
        n += 1

    if n == 0:
        return {"n": 0, "brier": None, "log_loss": None, "accuracy": None,
                "baseline_brier": None, "roi": None, "value_bets": 0,
                "reliability": []}

    roi = round((returned - staked) / staked, 4) if staked > 0 else None
    return {
        "n": n,
        "brier": round(brier_sum / n, 4),
        "log_loss": round(logloss_sum / n, 4),
        "accuracy": round(correct / n, 4),
        # Uniform-guess Brier for a 3-way market = 3 * ((1/3)^2 average) ≈ 0.667.
        "baseline_brier": 0.6667,
        "roi": roi,
        "value_bets": int(staked),
        "reliability": reliability_bins(rel_pairs),
    }
