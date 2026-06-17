from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.prediction import Prediction
from pipeline.models.ensemble import load_weights
from pipeline.features.backtest import backtest
from pipeline.features.calibration import compute_goal_calibration
from pipeline.features.dc_fit import load_dc_params
from pipeline.models.goals_gbm import load_holdout

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
            "Ensemble of Dixon-Coles (attack/defense fit on real recent results), "
            "a gradient-boosted Poisson goals model (trained on ~49k historical "
            "internationals, 1872–present), and an ELO term — weights learned by "
            "log-loss minimisation. ELOs are computed from real match history "
            "(World-Football-Elo style). Home edge applies only to the 2026 hosts "
            "(MX/USA/CAN); every other match is treated as neutral. A single "
            "global goal-level calibration keeps the scoring level honest."
        ),
    }


@router.get("/model/metrics")
def get_model_metrics(db: Session = Depends(get_db)):
    """Backtest metrics over played matches: Brier, log-loss, accuracy,
    reliability curve and betting ROI. Cheap enough to compute on request."""
    dc_params = load_dc_params() or _DC_FALLBACK
    calibration = compute_goal_calibration(db, dc_params)
    metrics = backtest(db, dc_params, calibration)
    metrics["calibration"] = {
        "goal_offset_home": round(calibration["off_home"], 4),
        "goal_offset_away": round(calibration["off_away"], 4),
        "calibrated_from": calibration["n"],
    }
    # The honest precision number: held-out test over thousands of historical
    # matches (the WC-only backtest above is far too small to trust).
    metrics["holdout"] = load_holdout()
    return metrics
