from pipeline.models.markets import compute_all_markets

def test_all_markets_present():
    dc_result = {
        "prob_home_win": 0.50, "prob_draw": 0.25, "prob_away_win": 0.25,
        "lambda_home": 1.8, "lambda_away": 1.1,
        "score_matrix": {"0-0": 0.05, "1-0": 0.12, "0-1": 0.08, "1-1": 0.10,
                         "2-0": 0.09, "2-1": 0.11, "3-0": 0.05}
    }
    result = compute_all_markets(dc_result)
    assert "over_15" in result
    assert "over_25" in result
    assert "over_35" in result
    assert "btts" in result
    assert "top_scores" in result
    assert len(result["top_scores"]) <= 10

def test_top_scores_sorted_by_probability():
    dc_result = {
        "prob_home_win": 0.50, "prob_draw": 0.25, "prob_away_win": 0.25,
        "lambda_home": 1.8, "lambda_away": 1.1,
        "score_matrix": {"1-0": 0.15, "2-1": 0.12, "0-0": 0.07, "1-1": 0.10}
    }
    result = compute_all_markets(dc_result)
    probs = [s["probability"] for s in result["top_scores"]]
    assert probs == sorted(probs, reverse=True)
