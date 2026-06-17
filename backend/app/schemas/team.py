from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_name: str | None
    country_code: str | None
    elo_rating: float
