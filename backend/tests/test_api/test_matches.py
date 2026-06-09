from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.main import app
from app.database import Base, get_db
from app.models.team import Team
from app.models.match import Match

TEST_DB = "sqlite:///./test_mundial.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def setup_function():
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    t1 = Team(id=1, external_id=1, name="Brazil", country_code="BRA", elo_rating=2050.0)
    t2 = Team(id=2, external_id=2, name="Argentina", country_code="ARG", elo_rating=2100.0)
    m = Match(
        id=1, external_id=1, home_team_id=1, away_team_id=2,
        kickoff_utc=datetime(2026, 6, 15, 18, 0),
        stage="GROUP_STAGE", group="C",
        venue_city="New York", played=False,
    )
    db.add_all([t1, t2, m])
    db.commit()
    db.close()


def teardown_function():
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_list_matches_returns_list():
    response = client.get("/api/matches")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_match_returns_teams():
    response = client.get("/api/match/1")
    assert response.status_code == 200
    data = response.json()
    assert data["home_team"]["name"] == "Brazil"
    assert data["away_team"]["name"] == "Argentina"


def test_get_match_not_found():
    response = client.get("/api/match/999")
    assert response.status_code == 404
