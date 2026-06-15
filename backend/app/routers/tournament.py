from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.tournament import simulate_tournament

router = APIRouter()


@router.get("/tournament/simulate")
def simulate(
    n: int = Query(2000, ge=200, le=20000),
    db: Session = Depends(get_db),
):
    return simulate_tournament(db, n=n)
