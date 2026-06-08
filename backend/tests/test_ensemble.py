from pipeline.models.ensemble import blend_predictions, compute_confidence

def test_blend_probabilities_sum_to_one():
    dc = {"prob_home_win": 0.50, "prob_draw": 0.25, "prob_away_win": 0.25}
    xgb = {"prob_home_win": 0.45, "prob_draw": 0.28, "prob_away_win": 0.27}
    result = blend_predictions(dc, xgb, elo_diff=100.0)
    total = result["prob_home_win"] + result["prob_draw"] + result["prob_away_win"]
    assert abs(total - 1.0) < 0.001

def test_blend_favors_weighted_average():
    dc = {"prob_home_win": 0.60, "prob_draw": 0.20, "prob_away_win": 0.20}
    xgb = {"prob_home_win": 0.40, "prob_draw": 0.30, "prob_away_win": 0.30}
    result = blend_predictions(dc, xgb, elo_diff=0.0)
    assert 0.40 < result["prob_home_win"] < 0.60

def test_confidence_high_when_models_agree():
    dc = {"prob_home_win": 0.70, "prob_draw": 0.15, "prob_away_win": 0.15}
    xgb = {"prob_home_win": 0.68, "prob_draw": 0.17, "prob_away_win": 0.15}
    conf = compute_confidence(dc, xgb)
    assert conf > 0.7

def test_confidence_low_when_models_disagree():
    dc = {"prob_home_win": 0.70, "prob_draw": 0.15, "prob_away_win": 0.15}
    xgb = {"prob_home_win": 0.25, "prob_draw": 0.35, "prob_away_win": 0.40}
    conf = compute_confidence(dc, xgb)
    assert conf < 0.5
