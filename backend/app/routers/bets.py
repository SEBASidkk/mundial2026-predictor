from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.bets import BestBetsOut, BetPickOut
from app.services.bets import best_bets

router = APIRouter()


@router.get("/bets/best", response_model=BestBetsOut)
def get_best_bets(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    picks = best_bets(db, limit=limit)
    return BestBetsOut(picks=[BetPickOut(**p) for p in picks])
