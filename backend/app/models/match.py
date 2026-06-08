from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, unique=True, index=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    kickoff_utc = Column(DateTime, nullable=False)
    stage = Column(String)
    group = Column(String)
    venue_city = Column(String)
    venue_country = Column(String)
    venue_altitude_m = Column(Float, default=0.0)
    home_goals = Column(Integer)
    away_goals = Column(Integer)
    played = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    prediction = relationship("Prediction", back_populates="match", uselist=False)
