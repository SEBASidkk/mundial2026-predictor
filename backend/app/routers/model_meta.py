from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.prediction import Prediction
from pipeline.models.ensemble import load_weights
from pipeline.features.backtest import backtest
from pipeline.features.calibration import compute_goal_calibration

router = APIRouter()

_DC_FALLBACK = {"attack": {}, "defense": {}, "home_advantage": 0.3, "rho": -0.1}


@router.get("/model/meta")
def get_model_meta(db: Session = Depends(get_db)):
    last_pred = db.query(func.max(Prediction.generated_at)).scalar()
    count = db.query(func.count(Prediction.id)).scalar()
    w_dc, w_xgb, w_elo = load_weights()
    return {
        "last_updated": last_pred.isoformat() if last_pred else None,
        "predictions_count": count,
        "model_version": 2,
        "ensemble_weights": {
            "dixon_coles": round(w_dc, 4),
            "xgboost": round(w_xgb, 4),
            "elo": round(w_elo, 4),
        },
        "weights_source": "learned (log-loss min on played matches)",
        "methodology": (
            "Dixon-Coles (1997) + ELO-logistic, weights learned by log-loss "
            "minimisation. Bivariate Poisson for exact scores. Goal rates scale "
            "with ELO (k=0.72); home edge applies only to the 2026 hosts "
            "(MX/USA/CAN) since every match is at a neutral North-American venue. "
            "Recency ELO re-rating + a single global goal-level calibration "
            "(no home/away asymmetry) keep the scoring level honest."
        ),
    }


@router.get("/model/metrics")
def get_model_metrics(db: Session = Depends(get_db)):
    """Backtest metrics over played matches: Brier, log-loss, accuracy,
    reliability curve and betting ROI. Cheap enough to compute on request."""
    calibration = compute_goal_calibration(db, _DC_FALLBACK)
    metrics = backtest(db, _DC_FALLBACK, calibration)
    metrics["calibration"] = {
        "goal_offset_home": round(calibration["off_home"], 4),
        "goal_offset_away": round(calibration["off_away"], 4),
        "calibrated_from": calibration["n"],
    }
    return metrics
