import math
from pipeline.models.dixon_coles import (
    low_score_correction,
    poisson_probability,
    dixon_coles_probability,
    predict_match,
    fit_dixon_coles,
)

def test_poisson_probability():
    p = poisson_probability(2, 2.0)
    assert abs(p - 0.2707) < 0.001

def test_low_score_correction_zero_zero():
    rho = -0.1
    p = low_score_correction(0, 0, 1.5, 1.2, rho)
    assert p != 1.0

def test_low_score_correction_high_scores_unchanged():
    p = low_score_correction(3, 2, 1.5, 1.2, -0.1)
    assert p == 1.0

def test_predict_match_probabilities_sum_to_one():
    result = predict_match(lambda_home=1.5, lambda_away=1.2, rho=-0.1, max_goals=8)
    total = result["prob_home_win"] + result["prob_draw"] + result["prob_away_win"]
    assert abs(total - 1.0) < 0.001

def test_predict_match_favored_team_higher_prob():
    result = predict_match(lambda_home=2.5, lambda_away=0.8, rho=-0.1)
    assert result["prob_home_win"] > result["prob_away_win"]

def test_fit_dixon_coles_returns_lambdas():
    matches = [
        {"home_id": 1, "away_id": 2, "home_goals": 2, "away_goals": 1},
        {"home_id": 2, "away_id": 1, "home_goals": 0, "away_goals": 3},
        {"home_id": 1, "away_id": 2, "home_goals": 1, "away_goals": 0},
    ]
    params = fit_dixon_coles(matches)
    assert "attack" in params
    assert "defense" in params
    assert "home_advantage" in params
    assert "rho" in params
