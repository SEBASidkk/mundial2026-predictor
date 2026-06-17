from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Dict, List, Optional


class BetPickOut(BaseModel):
    # model_prob/model_confidence collide with Pydantic's protected "model_"
    # namespace; opt out so the fields are allowed without warnings.
    model_config = ConfigDict(protected_namespaces=())

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
    prob_ci_low: float          # 95% credible interval on the simulated prob
    prob_ci_high: float
    kelly_fraction: float       # suggested stake as a share of bankroll
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


class MatchBestBet(BaseModel):
    """A single fixture (chronological) with its strongest data-backed pick."""
    match_id: int
    home_team: str
    away_team: str
    kickoff_utc: str
    stage: Optional[str] = None
    group: Optional[str] = None
    best_pick: SafeBetOut


class MatchBestBetsOut(BaseModel):
    n: int                       # simulations per match
    note: str
    matches: List[MatchBestBet]


class OutrightPick(BaseModel):
    team: str
    elo: int
    prob: float
    fair_odds: float


class OutrightsOut(BaseModel):
    n: int                       # tournaments simulated
    markets: Dict[str, List[OutrightPick]]
