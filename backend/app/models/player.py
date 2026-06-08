from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, unique=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    name = Column(String, nullable=False)
    position = Column(String)
    nationality = Column(String)
    form_rating = Column(Float)
    minutes_last_5 = Column(Integer, default=0)
    goals_last_5 = Column(Integer, default=0)
    assists_last_5 = Column(Integer, default=0)
    injured = Column(Boolean, default=False)
    suspended = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

    team = relationship("Team", back_populates="players")
