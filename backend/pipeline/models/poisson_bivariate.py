import math
from typing import Dict


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def compute_over_under(lambda_home: float, lambda_away: float,
                        max_goals: int = 10) -> Dict[str, float]:
    goal_probs = {}
    for total in range(max_goals * 2 + 1):
        p = 0.0
        for hg in range(total + 1):
            ag = total - hg
            if ag <= max_goals:
                p += _poisson_pmf(hg, lambda_home) * _poisson_pmf(ag, lambda_away)
        goal_probs[total] = p

    result = {}
    for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
        key = str(line).replace(".", "")
        over = sum(v for k, v in goal_probs.items() if k > line)
        under = sum(v for k, v in goal_probs.items() if k < line)
        result[f"over_{key}"] = round(over, 5)
        result[f"under_{key}"] = round(under, 5)
    return result


def compute_btts(lambda_home: float, lambda_away: float) -> Dict[str, float]:
    p_home_scores = 1 - _poisson_pmf(0, lambda_home)
    p_away_scores = 1 - _poisson_pmf(0, lambda_away)
    return {"prob_btts": round(p_home_scores * p_away_scores, 5)}


def compute_asian_handicap(lambda_home: float, lambda_away: float,
                            handicap: float = 0.0, max_goals: int = 10) -> Dict[str, float]:
    prob_home_cover = 0.0
    prob_push = 0.0
    prob_away_cover = 0.0

    for hg in range(max_goals + 1):
        for ag in range(max_goals + 1):
            p = _poisson_pmf(hg, lambda_home) * _poisson_pmf(ag, lambda_away)
            adjusted_margin = (hg + handicap) - ag
            if adjusted_margin > 0:
                prob_home_cover += p
            elif adjusted_margin == 0:
                prob_push += p
            else:
                prob_away_cover += p

    return {
        "prob_home_cover": round(prob_home_cover, 5),
        "prob_push": round(prob_push, 5),
        "prob_away_cover": round(prob_away_cover, 5),
    }
