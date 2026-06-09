from pydantic import BaseModel
from datetime import datetime
from app.schemas.team import TeamOut
from app.schemas.prediction import PredictionOut


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

    class Config:
        from_attributes = True


class MatchDetailOut(MatchOut):
    prediction: PredictionOut | None
