"""Tests for learned ensemble weights, confidence and persistence."""
import math

from pipeline.models.ensemble import (
    blend_predictions,
    compute_confidence,
    fit_ensemble_weights,
    save_weights,
    load_weights,
    DEFAULT_WEIGHTS,
)


def _probs(h, d, a):
    return {"prob_home_win": h, "prob_draw": d, "prob_away_win": a}


def test_blend_respects_custom_weights():
    dc = _probs(0.8, 0.1, 0.1)
    xgb = _probs(0.2, 0.2, 0.6)
    all_dc = blend_predictions(dc, xgb, 0.0, weights=(1.0, 0.0, 0.0))
    assert all_dc["prob_home_win"] > 0.7


def test_confidence_high_when_models_agree():
    conf = compute_confidence(_probs(0.70, 0.15, 0.15), _probs(0.68, 0.17, 0.15))
    assert conf > 0.6


def test_confidence_low_when_models_disagree():
    conf = compute_confidence(_probs(0.70, 0.15, 0.15), _probs(0.25, 0.35, 0.40))
    assert conf < 0.5


def test_fit_returns_default_when_too_few_samples():
    assert fit_ensemble_weights([], min_samples=12) == DEFAULT_WEIGHTS


def test_fit_weights_sum_to_one_and_improve_logloss():
    # Build samples where DC is consistently right and ELO/XGB wrong, so the
    # fitter should lean toward DC.
    samples = []
    for _ in range(40):
        dc = _probs(0.7, 0.2, 0.1)      # confident home
        xgb = _probs(0.2, 0.2, 0.6)     # confident away (wrong)
        samples.append((dc, xgb, 50.0, 0))  # outcome: home win
    w = fit_ensemble_weights(samples, min_samples=12)
    assert abs(sum(w) - 1.0) < 1e-6
    assert all(x >= -1e-9 for x in w)
    # DC weight should dominate since DC was the accurate model.
    assert w[0] >= w[1]


def test_weights_roundtrip(tmp_path, monkeypatch):
    import pipeline.models.ensemble as ens
    monkeypatch.setattr(ens, "_STATE_FILE", tmp_path / "state.json")
    ens.save_weights((0.5, 0.3, 0.2))
    assert ens.load_weights() == (0.5, 0.3, 0.2)
