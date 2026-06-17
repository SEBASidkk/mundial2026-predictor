"""API tests for standings, team lookup and match simulation endpoints."""
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.team import Team
from app.models.match import Match
from app.models.prediction import Prediction

TEST_DB = "sqlite:///./test_misc.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)
_prev = {}


def setup_function():
    _prev["ov"] = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    db.add_all([
        Team(id=1, external_id=1, name="Brazil", country_code="BRA", elo_rating=2050.0),
        Team(id=2, external_id=2, name="Bolivia", country_code="BOL", elo_rating=1500.0),
    ])
    # one played + one upcoming (with prediction for simulate)
    db.add(Match(
        id=1, external_id=1, home_team_id=1, away_team_id=2,
        kickoff_utc=datetime(2026, 6, 18, 18, 0), stage="GROUP_STAGE", group="A",
        venue_city="Dallas", played=True, home_goals=2, away_goals=1,
    ))
    db.add(Match(
        id=2, external_id=2, home_team_id=1, away_team_id=2,
        kickoff_utc=datetime(2026, 6, 25, 18, 0), stage="GROUP_STAGE", group="A",
        venue_city="Dallas", played=False,
    ))
    db.add(Prediction(
        match_id=2, prob_home_win=0.7, prob_draw=0.2, prob_away_win=0.1,
        lambda_home=2.2, lambda_away=0.7, score_matrix={}, model_confidence=0.8,
    ))
    db.commit()
    db.close()


def teardown_function():
    Base.metadata.drop_all(bind=engine)
    prev = _prev.get("ov")
    if prev is not None:
        app.dependency_overrides[get_db] = prev
    else:
        app.dependency_overrides.pop(get_db, None)


def test_standings_tally_from_results():
    r = client.get("/api/standings")
    assert r.status_code == 200
    rows = {s["name"]: s for s in r.json()["standings"]}
    assert rows["Brazil"]["W"] == 1 and rows["Brazil"]["Pts"] == 3
    assert rows["Bolivia"]["L"] == 1 and rows["Bolivia"]["Pts"] == 0
    assert rows["Brazil"]["GF"] == 2 and rows["Brazil"]["GA"] == 1


def test_team_lookup_and_404():
    assert client.get("/api/teams/1").json()["name"] == "Brazil"
    assert client.get("/api/teams/999").status_code == 404


def test_match_simulate_returns_distribution():
    r = client.get("/api/match/2/simulate?n=2000")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    s = body["result"]["home"] + body["result"]["draw"] + body["result"]["away"]
    assert abs(s - 1.0) < 0.05
    assert body["top_scores"]
    assert body["avg_goals_home"] > body["avg_goals_away"]


def test_match_detail_carries_bets():
    r = client.get("/api/match/2")
    assert r.status_code == 200
    assert r.json()["bets"]  # upcoming match → picks present
