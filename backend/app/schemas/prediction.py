from pydantic import BaseModel
from typing import Dict, List


class ScoreEntry(BaseModel):
    score: str
    probability: float


class MarketOut(BaseModel):
    result_1x2: Dict[str, float]
    over_05: float
    over_15: float
    over_25: float
    over_35: float
    over_45: float
    under_25: float
    btts: float
    top_scores: List[ScoreEntry]
    model_confidence: float


class PredictionOut(BaseModel):
    prob_home_win: float
    prob_draw: float
    prob_away_win: float
    lambda_home: float
    lambda_away: float
    markets: MarketOut
    model_confidence: float
    generated_at: str
