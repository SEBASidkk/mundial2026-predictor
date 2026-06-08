from typing import Dict, List

COMPETITION_WEIGHTS = {
    "WC": 1.5,
    "WCQ": 1.0,
    "CONFED": 0.85,
    "FRIENDLY": 0.5,
}


def expected_score(rating_a: float, rating_b: float) -> float:
    """Probability that team A beats team B."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def update_elo(
    home_rating: float,
    away_rating: float,
    result: str,  # "home", "draw", "away"
    k: float = 32,
    competition_weight: float = 1.0,
    goal_diff: int = 0,
) -> tuple[float, float]:
    """Return (new_home_rating, new_away_rating)."""
    e_home = expected_score(home_rating, away_rating)
    e_away = 1.0 - e_home

    if result == "home":
        s_home, s_away = 1.0, 0.0
    elif result == "away":
        s_home, s_away = 0.0, 1.0
    else:
        s_home, s_away = 0.5, 0.5

    gd_mult = 1.0
    if goal_diff >= 2:
        gd_mult = 1.5
    if goal_diff >= 3:
        gd_mult = 1.75

    effective_k = k * competition_weight * gd_mult

    new_home = home_rating + effective_k * (s_home - e_home)
    new_away = away_rating + effective_k * (s_away - e_away)
    return new_home, new_away


def compute_elo_ratings(
    matches: List[Dict],
    initial_ratings: Dict[int, float],
    k: float = 32,
) -> Dict[int, float]:
    """
    Compute ELO ratings from a chronologically ordered list of matches.
    Each match dict: {home_id, away_id, home_goals, away_goals, competition}
    """
    ratings = dict(initial_ratings)

    for m in matches:
        h, a = m["home_id"], m["away_id"]
        ratings.setdefault(h, 1500.0)
        ratings.setdefault(a, 1500.0)

        hg, ag = m["home_goals"], m["away_goals"]
        result = "home" if hg > ag else ("away" if ag > hg else "draw")
        weight = COMPETITION_WEIGHTS.get(m.get("competition", "FRIENDLY"), 0.5)

        new_h, new_a = update_elo(
            ratings[h], ratings[a],
            result=result,
            k=k,
            competition_weight=weight,
            goal_diff=abs(hg - ag),
        )
        ratings[h] = new_h
        ratings[a] = new_a

    return ratings
