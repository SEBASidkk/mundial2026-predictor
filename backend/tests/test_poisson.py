from pipeline.models.poisson_bivariate import compute_over_under, compute_btts, compute_asian_handicap

def test_over_under_probabilities_sum_to_one():
    result = compute_over_under(lambda_home=1.5, lambda_away=1.2)
    assert abs(result["over_25"] + result["under_25"] - 1.0) < 0.001

def test_high_lambda_more_likely_over():
    low = compute_over_under(0.5, 0.5)
    high = compute_over_under(2.5, 2.5)
    assert high["over_25"] > low["over_25"]

def test_btts_zero_lambda_impossible():
    result = compute_btts(lambda_home=0.0, lambda_away=1.5)
    assert result["prob_btts"] < 0.01

def test_btts_high_lambdas_likely():
    result = compute_btts(lambda_home=2.0, lambda_away=2.0)
    assert result["prob_btts"] > 0.5
