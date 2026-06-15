"""Unit tests for recency goal-level calibration (pure functions)."""
import math

import pytest

from pipeline.features.calibration import goal_offsets, team_base_lambdas


def test_offset_zero_when_model_matches_reality():
    actual = [(2, 1)] * 20
    predicted = [(2.0, 1.0)] * 20
    off_h, off_a = goal_offsets(actual, predicted)
    assert off_h == pytest.approx(0.0, abs=1e-6)
    assert off_a == pytest.approx(0.0, abs=1e-6)


def test_offset_positive_when_model_underpredicts():
    # actual scores higher than predicted → raise the level (offset > 0)
    actual = [(3, 1)] * 20
    predicted = [(1.5, 1.0)] * 20
    off_h, _ = goal_offsets(actual, predicted)
    assert off_h > 0


def test_offset_negative_when_model_overpredicts():
    actual = [(1, 0)] * 20
    predicted = [(2.0, 1.0)] * 20
    off_h, off_a = goal_offsets(actual, predicted)
    assert off_h < 0
    assert off_a < 0


def test_offset_clamped():
    actual = [(10, 0)] * 20
    predicted = [(0.5, 1.0)] * 20
    off_h, _ = goal_offsets(actual, predicted, clamp=0.4)
    assert off_h == pytest.approx(0.4)


def test_shrinkage_tempers_small_samples():
    # one extreme match: strong shrinkage should pull the offset toward 0
    actual = [(7, 1)]
    predicted = [(1.4, 1.0)]
    big_shrink = goal_offsets(actual, predicted, shrinkage=20.0)[0]
    small_shrink = goal_offsets(actual, predicted, shrinkage=1.0)[0]
    assert 0 < big_shrink < small_shrink


def test_offset_empty_inputs():
    assert goal_offsets([], []) == (0.0, 0.0)


def test_team_base_lambdas_home_advantage():
    dc = {"attack": {}, "defense": {}, "home_advantage": 0.3, "rho": -0.1}
    lam_h, lam_a = team_base_lambdas(1800, 1800, dc)
    # equal teams: home rate exceeds away purely from home advantage
    assert lam_h > lam_a
    assert lam_h / lam_a == pytest.approx(math.exp(0.3), abs=1e-6)


def test_team_base_lambdas_stronger_team_scores_more():
    dc = {"attack": {}, "defense": {}, "home_advantage": 0.0, "rho": -0.1}
    strong_h, strong_a = team_base_lambdas(2050, 1550, dc)
    assert strong_h > strong_a  # strong home outscores weak away
