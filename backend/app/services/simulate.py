"""Monte Carlo match simulator.

Samples final scores from independent Poisson(lambda) draws for each side using
the Dixon-Coles goal rates stored on the prediction, then aggregates outcomes.
This is a sampling view of the goal model — re-running gives slightly different
numbers (no fixed seed), which is the point of a simulator.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from app.models.match import Match

MAX_GOALS = 10  # clamp for the scoreline histogram


def simulate_match(match: Match, n: int = 10000) -> Dict:
    pred = match.prediction
    if pred is None:
        return {"n": 0, "available": False}

    lam_h = max(0.01, float(pred.lambda_home))
    lam_a = max(0.01, float(pred.lambda_away))

    rng = np.random.default_rng()
    gh = rng.poisson(lam_h, n)
    ga = rng.poisson(lam_a, n)

    home_wins = int(np.sum(gh > ga))
    draws = int(np.sum(gh == ga))
    away_wins = int(np.sum(gh < ga))

    total = gh + ga
    btts = int(np.sum((gh > 0) & (ga > 0)))

    # Top scorelines
    gh_c = np.clip(gh, 0, MAX_GOALS)
    ga_c = np.clip(ga, 0, MAX_GOALS)
    pair_idx = gh_c * (MAX_GOALS + 1) + ga_c
    counts = np.bincount(pair_idx, minlength=(MAX_GOALS + 1) ** 2)
    order = np.argsort(counts)[::-1]
    top_scores: List[Dict] = []
    for idx in order[:8]:
        c = int(counts[idx])
        if c == 0:
            break
        h, a = divmod(int(idx), MAX_GOALS + 1)
        top_scores.append({"score": f"{h}-{a}", "probability": round(c / n, 4)})

    # Total goals distribution (0..7+)
    goal_dist: List[Dict] = []
    for g in range(0, 8):
        cnt = int(np.sum(total == g)) if g < 7 else int(np.sum(total >= 7))
        label = f"{g}" if g < 7 else "7+"
        goal_dist.append({"goals": label, "probability": round(cnt / n, 4)})

    def pct(x: int) -> float:
        return round(x / n, 4)

    return {
        "n": n,
        "available": True,
        "home_team": match.home_team.name,
        "away_team": match.away_team.name,
        "lambda_home": round(lam_h, 3),
        "lambda_away": round(lam_a, 3),
        "result": {"home": pct(home_wins), "draw": pct(draws), "away": pct(away_wins)},
        "avg_goals_home": round(float(np.mean(gh)), 2),
        "avg_goals_away": round(float(np.mean(ga)), 2),
        "over_25": pct(int(np.sum(total > 2.5))),
        "btts": pct(btts),
        "top_scores": top_scores,
        "goal_distribution": goal_dist,
    }
