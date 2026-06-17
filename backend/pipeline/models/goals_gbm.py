"""Gradient-boosted Poisson goals model — the real ML member of the ensemble.

Two `HistGradientBoostingRegressor`s with Poisson loss predict the home and away
goal rates from pre-match features (ELO, ELO gap, neutral venue, recent scoring
and conceding form). Trained on the full historical results set, this replaces
the old hand-rolled "XGBoost" slot that was really just an ELO logistic.

The trained pair is pickled to `gbm_model.pkl` so the API can load it without
retraining; `train_and_save` is called from the pipeline.
"""
from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)

FEATURES = [
    "elo_home", "elo_away", "elo_diff", "neutral",
    "home_gf", "home_ga", "away_gf", "away_ga",
]
MODEL_PATH = Path(__file__).resolve().parents[2] / "gbm_model.pkl"
MIN_ROWS = 500


class GoalsGBM:
    """Wraps the two fitted regressors and the feature ordering."""

    def __init__(self, home_model, away_model):
        self.home_model = home_model
        self.away_model = away_model

    @staticmethod
    def _vec(elo_home: float, elo_away: float, neutral: bool,
             home_form: Tuple[float, float], away_form: Tuple[float, float]) -> np.ndarray:
        return np.array([[
            elo_home, elo_away, elo_home - elo_away, 1 if neutral else 0,
            home_form[0], home_form[1], away_form[0], away_form[1],
        ]], dtype=float)

    def predict(self, elo_home: float, elo_away: float, neutral: bool,
                home_form: Tuple[float, float], away_form: Tuple[float, float]) -> Tuple[float, float]:
        x = self._vec(elo_home, elo_away, neutral, home_form, away_form)
        lam_h = float(self.home_model.predict(x)[0])
        lam_a = float(self.away_model.predict(x)[0])
        # Clamp to a sane football range.
        return max(0.15, min(5.0, lam_h)), max(0.15, min(5.0, lam_a))


def train(feature_rows: List[Dict]) -> Optional[GoalsGBM]:
    """Fit the two Poisson regressors. Returns None if too little data."""
    if len(feature_rows) < MIN_ROWS:
        log.warning("Only %d rows (<%d) — skipping GBM training.", len(feature_rows), MIN_ROWS)
        return None
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
    except Exception as exc:  # noqa: BLE001
        log.warning("scikit-learn unavailable (%s) — skipping GBM.", exc)
        return None

    X = np.array([[r[f] for f in FEATURES] for r in feature_rows], dtype=float)
    y_home = np.array([r["home_goals"] for r in feature_rows], dtype=float)
    y_away = np.array([r["away_goals"] for r in feature_rows], dtype=float)

    def fit(y):
        m = HistGradientBoostingRegressor(
            loss="poisson", max_iter=300, learning_rate=0.05,
            max_depth=4, min_samples_leaf=40, l2_regularization=1.0,
            random_state=42,
        )
        m.fit(X, y)
        return m

    model = GoalsGBM(fit(y_home), fit(y_away))
    log.info("Trained Poisson-GBM goals model on %d matches.", len(feature_rows))
    return model


def save(model: GoalsGBM) -> None:
    try:
        with MODEL_PATH.open("wb") as f:
            pickle.dump(model, f)
    except OSError as exc:  # noqa: BLE001
        log.warning("Could not persist GBM model: %s", exc)


def load() -> Optional[GoalsGBM]:
    if not MODEL_PATH.exists():
        return None
    try:
        with MODEL_PATH.open("rb") as f:
            return pickle.load(f)
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not load GBM model: %s", exc)
        return None


def train_and_save(feature_rows: List[Dict]) -> Optional[GoalsGBM]:
    model = train(feature_rows)
    if model is not None:
        save(model)
    return model


METRICS_PATH = Path(__file__).resolve().parents[2] / "holdout_metrics.json"


def evaluate_holdout(feature_rows: List[Dict], test_frac: float = 0.15) -> Optional[Dict]:
    """Honest out-of-sample check: train on the older matches, score 1x2 on the
    most recent `test_frac` (rows are chronological). This is the real precision
    number — the 20-match World Cup backtest is far too small to trust."""
    import math

    n = len(feature_rows)
    cut = int(n * (1 - test_frac))
    if n < MIN_ROWS or n - cut < 100:
        return None
    from pipeline.models.dixon_coles import predict_match

    model = train(feature_rows[:cut])
    if model is None:
        return None

    brier = ll = 0.0
    correct = 0
    test = feature_rows[cut:]
    for r in test:
        lam_h, lam_a = model.predict(
            r["elo_home"], r["elo_away"], bool(r["neutral"]),
            (r["home_gf"], r["home_ga"]), (r["away_gf"], r["away_ga"]),
        )
        p = predict_match(lam_h, lam_a, rho=-0.1)
        pv = [p["prob_home_win"], p["prob_draw"], p["prob_away_win"]]
        hg, ag = r["home_goals"], r["away_goals"]
        o = 0 if hg > ag else (1 if hg == ag else 2)
        brier += sum((pv[i] - (1.0 if i == o else 0.0)) ** 2 for i in range(3))
        ll += -math.log(max(1e-9, pv[o]))
        if max(range(3), key=lambda i: pv[i]) == o:
            correct += 1
    m = len(test)
    return {
        "n": m,
        "brier": round(brier / m, 4),
        "baseline_brier": 0.6667,
        "log_loss": round(ll / m, 4),
        "accuracy": round(correct / m, 4),
    }


def save_holdout(metrics: Dict) -> None:
    try:
        METRICS_PATH.write_text(json.dumps(metrics))
    except OSError as exc:  # noqa: BLE001
        log.warning("Could not persist holdout metrics: %s", exc)


def load_holdout() -> Optional[Dict]:
    try:
        return json.loads(METRICS_PATH.read_text())
    except (OSError, ValueError):
        return None
