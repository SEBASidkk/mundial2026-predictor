from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timezone


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), unique=True)
    model_version = Column(Integer, default=1)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    prob_home_win = Column(Float)
    prob_draw = Column(Float)
    prob_away_win = Column(Float)
    lambda_home = Column(Float)
    lambda_away = Column(Float)
    prob_over_05 = Column(Float)
    prob_over_15 = Column(Float)
    prob_over_25 = Column(Float)
    prob_over_35 = Column(Float)
    prob_over_45 = Column(Float)
    prob_btts = Column(Float)
    score_matrix = Column(JSON)
    model_confidence = Column(Float)

    match = relationship("Match", back_populates="prediction")
