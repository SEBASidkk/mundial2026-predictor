import math
import numpy as np
from scipy.optimize import minimize
from typing import Dict, List


def poisson_probability(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def low_score_correction(home_goals: int, away_goals: int,
                          lambda_home: float, lambda_away: float,
                          rho: float) -> float:
    if home_goals == 0 and away_goals == 0:
        return 1 - lambda_home * lambda_away * rho
    elif home_goals == 1 and away_goals == 0:
        return 1 + lambda_away * rho
    elif home_goals == 0 and away_goals == 1:
        return 1 + lambda_home * rho
    elif home_goals == 1 and away_goals == 1:
        return 1 - rho
    return 1.0


def dixon_coles_probability(home_goals: int, away_goals: int,
                             lambda_home: float, lambda_away: float,
                             rho: float) -> float:
    tau = low_score_correction(home_goals, away_goals, lambda_home, lambda_away, rho)
    return (tau *
            poisson_probability(home_goals, lambda_home) *
            poisson_probability(away_goals, lambda_away))


def predict_match(lambda_home: float, lambda_away: float,
                  rho: float = -0.1, max_goals: int = 8) -> Dict:
    score_matrix = {}
    prob_home_win = 0.0
    prob_draw = 0.0
    prob_away_win = 0.0

    for hg in range(max_goals + 1):
        for ag in range(max_goals + 1):
            p = dixon_coles_probability(hg, ag, lambda_home, lambda_away, rho)
            score_matrix[f"{hg}-{ag}"] = round(p, 5)
            if hg > ag:
                prob_home_win += p
            elif hg == ag:
                prob_draw += p
            else:
                prob_away_win += p

    total = prob_home_win + prob_draw + prob_away_win
    return {
        "prob_home_win": prob_home_win / total,
        "prob_draw": prob_draw / total,
        "prob_away_win": prob_away_win / total,
        "score_matrix": score_matrix,
        "lambda_home": lambda_home,
        "lambda_away": lambda_away,
    }


def _neg_log_likelihood(params: np.ndarray, matches: List[Dict],
                         team_ids: List[int]) -> float:
    n = len(team_ids)
    attack = {t: params[i] for i, t in enumerate(team_ids)}
    defense = {t: params[n + i] for i, t in enumerate(team_ids)}
    home_adv = params[2 * n]
    rho = params[2 * n + 1]

    log_lik = 0.0
    for m in matches:
        h, a = m["home_id"], m["away_id"]
        lam_h = math.exp(attack[h] - defense[a] + home_adv)
        lam_a = math.exp(attack[a] - defense[h])
        p = dixon_coles_probability(m["home_goals"], m["away_goals"], lam_h, lam_a, rho)
        if p <= 0:
            return 1e10
        log_lik += math.log(p)
    return -log_lik


def fit_dixon_coles(matches: List[Dict]) -> Dict:
    team_ids = list({m["home_id"] for m in matches} | {m["away_id"] for m in matches})
    n = len(team_ids)
    x0 = np.array([0.1] * n + [0.1] * n + [0.3, -0.1])
    bounds = ([(None, None)] * (2 * n) + [(0.0, 1.0), (-0.5, 0.0)])

    result = minimize(
        _neg_log_likelihood,
        x0,
        args=(matches, team_ids),
        method="L-BFGS-B",
        bounds=bounds,
    )

    attack = {t: result.x[i] for i, t in enumerate(team_ids)}
    defense = {t: result.x[n + i] for i, t in enumerate(team_ids)}
    return {
        "attack": attack,
        "defense": defense,
        "home_advantage": float(result.x[2 * n]),
        "rho": float(result.x[2 * n + 1]),
    }
