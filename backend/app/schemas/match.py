from __future__ import annotations

from pydantic import BaseModel
from datetime import datetime
from typing import List
from app.schemas.team import TeamOut
from app.schemas.prediction import PredictionOut
from app.schemas.bets import BetPickOut


class MatchOut(BaseModel):
    id: int
    home_team: TeamOut
    away_team: TeamOut
    kickoff_utc: datetime
    stage: str | None
    group: str | None
    venue_city: str | None
    played: bool
    home_goals: int | None
    away_goals: int | None
    prediction: PredictionOut | None = None

    class Config:
        from_attributes = True


class MatchDetailOut(MatchOut):
    bets: List[BetPickOut] = []
