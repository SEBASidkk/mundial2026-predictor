"""Recency calibration from real results.

The free data tier ships no historical matches, so team strengths come from
seed ELOs and the global goal level is uncontrolled — in practice the model
under-predicts goals and skews every market toward "Under". This module fixes
that empirically using the matches that have *already been played this
tournament*:

  1. `updated_elos` re-rates teams from their actual results on top of the seed
     prior (recency — recent form moves the ratings).
  2. `goal_offsets` compares the model's predicted goal rates against what was
     actually scored and returns multiplicative log-offsets for the home and
     away goal levels, shrunk toward 1.0 so a small, noisy sample (or a single
     blowout) can't swing the calibration wildly.

Both are applied in the pipeline so predictions track reality instead of a
fixed, too-low prior.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.team import Team
from pipeline.features.elo import compute_elo_ratings
from pipeline.features.seed_ratings import strengths_from_elo


def played_matches(db: Session) -> List[Dict]:
    """Finished matches with a real scoreline, oldest first (by kickoff)."""
    rows = (
        db.query(Match)
        .filter(Match.played == True)  # noqa: E712
        .filter(Match.home_goals.isnot(None))
        .order_by(Match.kickoff_utc.asc())
        .all()
    )
    return [
        {
            "home_id": m.home_team_id,
            "away_id": m.away_team_id,
            "home_goals": m.home_goals,
            "away_goals": m.away_goals,
            "competition": "WC",
        }
        for m in rows
    ]


def updated_elos(db: Session) -> Dict[int, float]:
    """Team ELOs after applying this tournament's real results to the seed prior.

    Returns {team_id: rating}. Caller persists them onto Team.elo_rating.
    """
    initial = {t.id: float(t.elo_rating) for t in db.query(Team).all()}
    matches = played_matches(db)
    if not matches:
        return initial
    return compute_elo_ratings(matches, initial)


def team_base_lambdas(
    home_elo: float,
    away_elo: float,
    dc_params: Dict,
    home_ext: Optional[int] = None,
    away_ext: Optional[int] = None,
) -> Tuple[float, float]:
    """Pre-calibration goal rates for a fixture (shared by fit + calibration).

    Uses fitted Dixon-Coles attack/defense when available, else ELO-derived
    strengths. Mirrors the formula used when generating predictions.
    """
    h = strengths_from_elo(home_elo)
    a = strengths_from_elo(away_elo)
    h_att = dc_params["attack"].get(home_ext, h["attack"])
    h_def = dc_params["defense"].get(home_ext, h["defense"])
    a_att = dc_params["attack"].get(away_ext, a["attack"])
    a_def = dc_params["defense"].get(away_ext, a["defense"])
    lam_h = math.exp(h_att - a_def + dc_params["home_advantage"])
    lam_a = math.exp(a_att - h_def)
    return lam_h, lam_a


def goal_offsets(
    actual: List[Tuple[int, int]],
    predicted: List[Tuple[float, float]],
    shrinkage: float = 8.0,
    clamp: float = 0.4,
) -> Tuple[float, float]:
    """Log goal-level offsets (home, away) from actual vs predicted goals.

    `actual` and `predicted` are aligned lists of (home, away) pairs. The offset
    is log of a shrunk ratio (sum_actual + s) / (sum_pred + s); adding the same
    pseudo-count `s` to both pulls the ratio toward 1.0 for small/noisy samples.
    Result is clamped to ±`clamp` so calibration nudges rather than overrides.
    """
    if not actual or not predicted:
        return 0.0, 0.0

    sum_ah = sum(a[0] for a in actual)
    sum_aa = sum(a[1] for a in actual)
    sum_ph = sum(p[0] for p in predicted)
    sum_pa = sum(p[1] for p in predicted)

    def offset(sum_actual: float, sum_pred: float) -> float:
        ratio = (sum_actual + shrinkage) / (sum_pred + shrinkage)
        return max(-clamp, min(clamp, math.log(ratio)))

    return offset(sum_ah, sum_ph), offset(sum_aa, sum_pa)


def compute_goal_calibration(
    db: Session,
    dc_params: Dict,
    shrinkage: float = 8.0,
    clamp: float = 0.4,
) -> Dict:
    """Calibration offsets from played matches: predict each with the current
    model, compare to the real scoreline, return {off_home, off_away, n}."""
    teams = {t.id: t for t in db.query(Team).all()}
    matches = played_matches(db)
    actual: List[Tuple[int, int]] = []
    predicted: List[Tuple[float, float]] = []
    for m in matches:
        h = teams.get(m["home_id"])
        a = teams.get(m["away_id"])
        if h is None or a is None:
            continue
        lam_h, lam_a = team_base_lambdas(
            h.elo_rating, a.elo_rating, dc_params, h.external_id, a.external_id
        )
        predicted.append((lam_h, lam_a))
        actual.append((m["home_goals"], m["away_goals"]))

    off_h, off_a = goal_offsets(actual, predicted, shrinkage=shrinkage, clamp=clamp)
    return {"off_home": off_h, "off_away": off_a, "n": len(actual)}
