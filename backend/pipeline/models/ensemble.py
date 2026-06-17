"""Weighted ensemble of the 1x2 sub-models (Dixon-Coles, ELO-logistic, XGB slot).

Weights are no longer hand-picked: `fit_ensemble_weights` learns them by
minimising multiclass log-loss on played matches (the only labelled data the
free tier gives us), constrained to a probability simplex so they stay
interpretable. When too few matches exist to fit reliably, the module falls
back to sensible defaults. The learned weights are persisted to a small JSON
state file so the API (and the model-meta endpoint) report what was actually
used, not a hard-coded guess.

`compute_confidence` combines two independent signals:
  * agreement  — how closely the sub-models concur (low L1 divergence), and
  * sharpness  — how peaked the blended distribution is (low entropy),
so a confident pick needs the models both to agree *and* to commit.
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# Sensible priors, used until enough results exist to learn better ones.
DEFAULT_WEIGHTS: Tuple[float, float, float] = (0.40, 0.35, 0.25)  # DC, XGB/ELO-1x2, ELO

_STATE_FILE = Path(__file__).resolve().parents[2] / "model_state.json"
_ELO_DRAW_BASE = 0.26


def elo_to_prob(elo_diff: float) -> float:
    return 1.0 / (1.0 + 10 ** (-elo_diff / 400.0))


def _elo_1x2(elo_diff: float) -> Dict[str, float]:
    """ELO-logistic mapped to a 1x2 distribution with a fixed draw mass."""
    home = elo_to_prob(elo_diff)
    return {
        "prob_home_win": home * (1 - _ELO_DRAW_BASE),
        "prob_draw": _ELO_DRAW_BASE,
        "prob_away_win": (1 - home) * (1 - _ELO_DRAW_BASE),
    }


def blend_predictions(
    dc: Dict[str, float],
    xgb: Dict[str, float],
    elo_diff: float,
    weights: Optional[Tuple[float, float, float]] = None,
) -> Dict[str, float]:
    """Convex blend of the three sub-models, renormalised to sum to 1."""
    w_dc, w_xgb, w_elo = weights or DEFAULT_WEIGHTS
    elo = _elo_1x2(elo_diff)

    out = {}
    for key in ("prob_home_win", "prob_draw", "prob_away_win"):
        out[key] = w_dc * dc[key] + w_xgb * xgb[key] + w_elo * elo[key]
    total = sum(out.values()) or 1.0
    return {k: v / total for k, v in out.items()}


def _entropy_sharpness(probs: Dict[str, float]) -> float:
    """1 - normalised Shannon entropy of a 3-way distribution → [0, 1]."""
    vals = [max(1e-9, probs[k]) for k in ("prob_home_win", "prob_draw", "prob_away_win")]
    s = sum(vals)
    vals = [v / s for v in vals]
    h = -sum(v * math.log(v) for v in vals)
    return max(0.0, 1.0 - h / math.log(3))


def compute_confidence(
    dc: Dict[str, float],
    xgb: Dict[str, float],
    blended: Optional[Dict[str, float]] = None,
) -> float:
    """Confidence in [0, 1]: 70% sub-model agreement, 30% distribution sharpness."""
    divergence = sum(
        abs(dc[k] - xgb[k])
        for k in ("prob_home_win", "prob_draw", "prob_away_win")
    )
    agreement = max(0.0, 1.0 - divergence)
    if blended is None:
        blended = {k: (dc[k] + xgb[k]) / 2 for k in dc}
    sharpness = _entropy_sharpness(blended)
    return round(0.7 * agreement + 0.3 * sharpness, 4)


# --------------------------------------------------------------------------- #
# Weight learning
# --------------------------------------------------------------------------- #
_OUTCOME_KEYS = ("prob_home_win", "prob_draw", "prob_away_win")


def _logloss(samples: List[Tuple[Dict, Dict, float, int]],
             weights: Tuple[float, float, float]) -> float:
    """Mean multiclass log-loss of the blended model over labelled samples.

    Each sample is (dc_probs, xgb_probs, elo_diff, outcome) where outcome is
    0=home, 1=draw, 2=away.
    """
    total = 0.0
    for dc, xgb, elo_diff, outcome in samples:
        blended = blend_predictions(dc, xgb, elo_diff, weights)
        p = max(1e-9, blended[_OUTCOME_KEYS[outcome]])
        total += -math.log(p)
    return total / len(samples)


def fit_ensemble_weights(
    samples: List[Tuple[Dict, Dict, float, int]],
    min_samples: int = 12,
    prior_strength: float = 20.0,
) -> Tuple[float, float, float]:
    """Learn simplex weights minimising log-loss; default when data is thin.

    Uses scipy SLSQP over the 2-simplex when available, else a coarse grid
    search — both constrained so weights are non-negative and sum to 1. The
    fitted weights are then shrunk toward the defaults with weight
    n / (n + prior_strength): with few matches a degenerate corner solution
    (e.g. all weight on one model) is pulled back toward a sensible blend, and
    the data only fully takes over once there are many results.
    """
    if len(samples) < min_samples:
        log.info("Only %d labelled matches (<%d) — keeping default ensemble weights.",
                 len(samples), min_samples)
        return DEFAULT_WEIGHTS

    best = DEFAULT_WEIGHTS
    try:
        from scipy.optimize import minimize  # type: ignore

        def obj(x):
            w = (x[0], x[1], max(0.0, 1.0 - x[0] - x[1]))
            return _logloss(samples, w)

        res = minimize(
            obj, x0=[0.4, 0.35], method="SLSQP",
            bounds=[(0.0, 1.0), (0.0, 1.0)],
            constraints=[{"type": "ineq", "fun": lambda x: 1.0 - x[0] - x[1]}],
        )
        if res.success:
            w0, w1 = float(res.x[0]), float(res.x[1])
            best = (w0, w1, max(0.0, 1.0 - w0 - w1))
    except Exception as exc:  # noqa: BLE001 — fall back to grid
        log.warning("scipy weight fit failed (%s); grid searching.", exc)
        best_loss = float("inf")
        step = 0.05
        i = 0.0
        while i <= 1.0:
            j = 0.0
            while i + j <= 1.0:
                w = (i, j, 1.0 - i - j)
                loss = _logloss(samples, w)
                if loss < best_loss:
                    best_loss, best = loss, w
                j += step
            i += step

    # Renormalise against tiny float drift.
    s = sum(best) or 1.0
    best = (best[0] / s, best[1] / s, best[2] / s)

    # Shrink toward the defaults so a small sample can't collapse onto one model.
    n = len(samples)
    w_data = n / (n + prior_strength)
    blended = tuple(
        w_data * b + (1.0 - w_data) * d
        for b, d in zip(best, DEFAULT_WEIGHTS)
    )
    bs = sum(blended) or 1.0
    return (blended[0] / bs, blended[1] / bs, blended[2] / bs)


def save_weights(weights: Tuple[float, float, float]) -> None:
    try:
        _STATE_FILE.write_text(json.dumps({
            "dixon_coles": round(weights[0], 4),
            "xgboost": round(weights[1], 4),
            "elo": round(weights[2], 4),
        }))
    except OSError as exc:  # noqa: BLE001
        log.warning("Could not persist ensemble weights: %s", exc)


def load_weights() -> Tuple[float, float, float]:
    try:
        d = json.loads(_STATE_FILE.read_text())
        return (d["dixon_coles"], d["xgboost"], d["elo"])
    except (OSError, ValueError, KeyError):
        return DEFAULT_WEIGHTS
