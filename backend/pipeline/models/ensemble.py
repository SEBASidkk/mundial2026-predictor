from typing import Dict

W_DC = 0.40
W_XGB = 0.35
W_ELO = 0.25


def elo_to_prob(elo_diff: float) -> float:
    return 1.0 / (1.0 + 10 ** (-elo_diff / 400.0))


def blend_predictions(
    dc: Dict[str, float],
    xgb: Dict[str, float],
    elo_diff: float,
) -> Dict[str, float]:
    elo_home = elo_to_prob(elo_diff)
    elo_draw_base = 0.26
    elo_home_adj = elo_home * (1 - elo_draw_base)
    elo_away_adj = (1 - elo_home) * (1 - elo_draw_base)

    blended_home = (
        W_DC * dc["prob_home_win"] +
        W_XGB * xgb["prob_home_win"] +
        W_ELO * elo_home_adj
    )
    blended_draw = (
        W_DC * dc["prob_draw"] +
        W_XGB * xgb["prob_draw"] +
        W_ELO * elo_draw_base
    )
    blended_away = (
        W_DC * dc["prob_away_win"] +
        W_XGB * xgb["prob_away_win"] +
        W_ELO * elo_away_adj
    )

    total = blended_home + blended_draw + blended_away
    return {
        "prob_home_win": blended_home / total,
        "prob_draw": blended_draw / total,
        "prob_away_win": blended_away / total,
    }


def compute_confidence(dc: Dict[str, float], xgb: Dict[str, float]) -> float:
    divergence = (
        abs(dc["prob_home_win"] - xgb["prob_home_win"]) +
        abs(dc["prob_draw"] - xgb["prob_draw"]) +
        abs(dc["prob_away_win"] - xgb["prob_away_win"])
    )
    return max(0.0, 1.0 - divergence)
