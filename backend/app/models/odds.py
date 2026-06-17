from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timezone


class Odds(Base):
    """Real bookmaker odds for a single match market selection.

    One row per (match, market, selection). Populated from The Odds API.
    When absent, the bets service falls back to fair odds (1 / model prob).
    """
    __tablename__ = "odds"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), index=True, nullable=False)
    market = Column(String, nullable=False)      # e.g. "1x2", "over_25", "btts"
    selection = Column(String, nullable=False)   # e.g. "home", "draw", "away", "yes", "over"
    decimal_odds = Column(Float, nullable=False)
    bookmaker = Column(String)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    match = relationship("Match")
