from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.prediction import Prediction

router = APIRouter()


@router.get("/model/meta")
def get_model_meta(db: Session = Depends(get_db)):
    last_pred = db.query(func.max(Prediction.generated_at)).scalar()
    count = db.query(func.count(Prediction.id)).scalar()
    return {
        "last_updated": last_pred.isoformat() if last_pred else None,
        "predictions_count": count,
        "model_version": 1,
        "ensemble_weights": {"dixon_coles": 0.40, "xgboost": 0.35, "elo": 0.25},
        "methodology": "Dixon-Coles (1997) + ELO + XGBoost ensemble. Bivariate Poisson for exact scores.",
    }
