from typing import Dict
from pipeline.models.poisson_bivariate import compute_over_under, compute_btts, compute_asian_handicap


def compute_all_markets(dc_result: Dict) -> Dict:
    lh = dc_result["lambda_home"]
    la = dc_result["lambda_away"]

    ou = compute_over_under(lh, la)
    btts = compute_btts(lh, la)
    ah_0 = compute_asian_handicap(lh, la, handicap=0.0)
    ah_neg05 = compute_asian_handicap(lh, la, handicap=-0.5)
    ah_plus05 = compute_asian_handicap(lh, la, handicap=0.5)

    score_matrix = dc_result.get("score_matrix", {})
    top_scores = sorted(
        [{"score": k, "probability": round(v, 5)} for k, v in score_matrix.items()],
        key=lambda x: x["probability"],
        reverse=True,
    )[:10]

    return {
        "result_1x2": {
            "home": round(dc_result["prob_home_win"], 5),
            "draw": round(dc_result["prob_draw"], 5),
            "away": round(dc_result["prob_away_win"], 5),
        },
        "over_05": ou["over_05"],
        "over_15": ou["over_15"],
        "over_25": ou["over_25"],
        "over_35": ou["over_35"],
        "over_45": ou["over_45"],
        "under_05": ou["under_05"],
        "under_15": ou["under_15"],
        "under_25": ou["under_25"],
        "under_35": ou["under_35"],
        "under_45": ou["under_45"],
        "btts": btts["prob_btts"],
        "asian_handicap_0": ah_0,
        "asian_handicap_neg05": ah_neg05,
        "asian_handicap_plus05": ah_plus05,
        "top_scores": top_scores,
    }
