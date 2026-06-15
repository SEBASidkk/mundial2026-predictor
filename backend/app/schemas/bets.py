from __future__ import annotations

from pydantic import BaseModel
from typing import Dict, List, Optional


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


class SafeBetOut(BetPickOut):
    """A best-bet pick enriched with the simulation-backed safety signals."""
    model_confidence: float
    safety_score: float
    exp_goals_home: float
    exp_goals_away: float
    exp_goals_total: float
    rationale: str


class SafeBetsOut(BaseModel):
    n: int                       # simulations per match
    note: str
    picks: List[SafeBetOut]


class ParlayOut(BaseModel):
    legs: List[SafeBetOut]
    combined_prob: float
    combined_odds: float
    fair_odds: float
    expected_value: float        # per unit stake; >0 => positive value


class OutrightPick(BaseModel):
    team: str
    elo: int
    prob: float
    fair_odds: float


class OutrightsOut(BaseModel):
    n: int                       # tournaments simulated
    markets: Dict[str, List[OutrightPick]]
