from pipeline.features.elo import (
    expected_score,
    update_elo,
    compute_elo_ratings,
)


def test_expected_score_equal_ratings():
    assert abs(expected_score(1500, 1500) - 0.5) < 0.001


def test_expected_score_higher_rating_wins():
    assert expected_score(1600, 1400) > 0.5
    assert expected_score(1400, 1600) < 0.5


def test_update_elo_winner_gains():
    new_home, new_away = update_elo(1500, 1500, result="home", k=32, competition_weight=1.0)
    assert new_home > 1500
    assert new_away < 1500


def test_update_elo_draw_near_equal():
    new_home, new_away = update_elo(1500, 1500, result="draw", k=32, competition_weight=1.0)
    assert abs(new_home - 1500) < 5
    assert abs(new_away - 1500) < 5


def test_compute_elo_ratings_chronological():
    matches = [
        {"home_id": 1, "away_id": 2, "home_goals": 2, "away_goals": 0, "competition": "WC"},
        {"home_id": 2, "away_id": 3, "home_goals": 1, "away_goals": 1, "competition": "WC"},
    ]
    initial = {1: 1500.0, 2: 1500.0, 3: 1500.0}
    ratings = compute_elo_ratings(matches, initial.copy())
    assert ratings[1] > ratings[2]
    assert ratings[1] > ratings[3]
