from __future__ import annotations

from pydantic import BaseModel
from typing import List, Optional


class BetPickOut(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    kickoff_utc: str
    market: str
    selection: str
    label: str
    model_prob: float
    decimal_odds: float
    implied_prob: float
    edge: float
    source: str                 # "market" (real) | "fair" (derived)
    bookmaker: Optional[str] = None


class BestBetsOut(BaseModel):
    picks: List[BetPickOut]
