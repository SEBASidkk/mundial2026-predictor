from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.bets import (
    BestBetsOut,
    BetPickOut,
    SafeBetOut,
    SafeBetsOut,
    ParlayOut,
    OutrightsOut,
)
from app.services.bets import best_bets
from app.services.safe_bets import safe_bets, build_parlay, outright_bets

router = APIRouter()

_SAFE_NOTE = (
    "Picks rankeados por probabilidad simulada (Monte Carlo) y valor vs odds. "
    "Ninguna apuesta es 100% segura — son las estadísticamente más fuertes."
)


@router.get("/bets/best", response_model=BestBetsOut)
def get_best_bets(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    picks = best_bets(db, limit=limit)
    return BestBetsOut(picks=[BetPickOut(**p) for p in picks])


@router.get("/bets/safe", response_model=SafeBetsOut)
def get_safe_bets(
    limit: int = Query(20, ge=1, le=100),
    n: int = Query(10000, ge=1000, le=100000),
    per_match: int = Query(1, ge=1, le=5),
    value_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    picks = safe_bets(db, limit=limit, n=n, per_match=per_match, value_only=value_only)
    return SafeBetsOut(
        n=n,
        note=_SAFE_NOTE,
        picks=[SafeBetOut(**p) for p in picks],
    )


@router.get("/bets/parlay", response_model=ParlayOut)
def get_parlay(
    legs: int = Query(3, ge=2, le=8),
    n: int = Query(10000, ge=1000, le=100000),
    pool: int = Query(40, ge=2, le=100),
    db: Session = Depends(get_db),
):
    picks = safe_bets(db, limit=pool, n=n, per_match=1)
    parlay = build_parlay(picks, legs=legs)
    parlay["legs"] = [SafeBetOut(**leg) for leg in parlay["legs"]]
    return ParlayOut(**parlay)


@router.get("/bets/outrights", response_model=OutrightsOut)
def get_outrights(
    n: int = Query(3000, ge=500, le=20000),
    top: int = Query(10, ge=1, le=48),
    db: Session = Depends(get_db),
):
    return OutrightsOut(**outright_bets(db, n=n, top=top))
