from pydantic import BaseModel


class TeamOut(BaseModel):
    id: int
    name: str
    short_name: str | None
    country_code: str | None
    elo_rating: float

    class Config:
        from_attributes = True
