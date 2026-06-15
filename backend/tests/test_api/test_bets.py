from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.team import Team
from app.models.match import Match
from app.models.prediction import Prediction

TEST_DB = "sqlite:///./test_bets.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)
_prev_override = {}


def _seed_match(db, mid, home_id, away_id, lam_h, lam_a, conf=0.9):
    db.add(Match(
        id=mid, external_id=mid, home_team_id=home_id, away_team_id=away_id,
        kickoff_utc=datetime(2026, 6, 20, 18, 0),
        stage="GROUP_STAGE", group="A", venue_city="Dallas", played=False,
    ))
    db.add(Prediction(
        match_id=mid,
        prob_home_win=0.7, prob_draw=0.2, prob_away_win=0.1,
        lambda_home=lam_h, lambda_away=lam_a,
        score_matrix={}, model_confidence=conf,
    ))


def setup_function():
    # dependency_overrides is global; other test files set their own at import
    # time. Install ours for the duration of this file's tests and restore after
    # so we don't clobber (or get clobbered by) the others or hit the real DB.
    _prev_override["ov"] = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    db.add_all([
        Team(id=1, external_id=1, name="Brazil", country_code="BRA", elo_rating=2050.0),
        Team(id=2, external_id=2, name="Bolivia", country_code="BOL", elo_rating=1500.0),
        Team(id=3, external_id=3, name="France", country_code="FRA", elo_rating=2030.0),
        Team(id=4, external_id=4, name="Panama", country_code="PAN", elo_rating=1550.0),
    ])
    _seed_match(db, 1, 1, 2, lam_h=2.4, lam_a=0.5)   # Brazil strong favourite
    _seed_match(db, 2, 3, 4, lam_h=2.2, lam_a=0.6)   # France strong favourite
    db.commit()
    db.close()


def teardown_function():
    Base.metadata.drop_all(bind=engine)
    prev = _prev_override.get("ov")
    if prev is not None:
        app.dependency_overrides[get_db] = prev
    else:
        app.dependency_overrides.pop(get_db, None)


def test_safe_bets_returns_ranked_picks():
    r = client.get("/api/bets/safe?limit=10&n=4000")
    assert r.status_code == 200
    body = r.json()
    assert body["n"] == 4000
    assert "segura" in body["note"].lower()
    picks = body["picks"]
    assert len(picks) >= 1
    # ranked by safety score, descending
    scores = [p["safety_score"] for p in picks]
    assert scores == sorted(scores, reverse=True)
    top = picks[0]
    for field in ("model_prob", "safety_score", "model_confidence", "edge", "decimal_odds"):
        assert field in top
    assert 0.0 <= top["model_prob"] <= 1.0


def test_safe_bets_favourite_surfaces():
    r = client.get("/api/bets/safe?limit=20&n=8000&per_match=3")
    picks = r.json()["picks"]
    # a strong favourite's home win should appear and be high probability
    home_wins = [p for p in picks if p["market"] == "1x2" and p["selection"] == "home"]
    assert home_wins
    assert max(p["model_prob"] for p in home_wins) > 0.6


def test_safe_bets_carry_rationale_and_goals():
    r = client.get("/api/bets/safe?limit=10&n=4000")
    picks = r.json()["picks"]
    assert picks
    top = picks[0]
    assert isinstance(top["rationale"], str) and len(top["rationale"]) > 10
    assert top["exp_goals_total"] > 0
    assert "%" in top["rationale"]


def test_safe_bets_value_only_filters_to_positive_edge():
    # no odds seeded in this test DB → all picks are fair → value_only empties it
    r = client.get("/api/bets/safe?limit=10&n=4000&value_only=true")
    assert r.status_code == 200
    assert r.json()["picks"] == []


def test_parlay_combines_independent_legs():
    r = client.get("/api/bets/parlay?legs=2&n=4000")
    assert r.status_code == 200
    body = r.json()
    assert len(body["legs"]) == 2
    # legs come from distinct matches
    assert len({leg["match_id"] for leg in body["legs"]}) == 2
    # combined prob equals the product of leg probabilities
    prod = body["legs"][0]["model_prob"] * body["legs"][1]["model_prob"]
    assert abs(body["combined_prob"] - prod) < 1e-4
    assert body["combined_odds"] > 1.0


def test_outrights_degrade_gracefully_on_partial_data():
    # only 1 group seeded → no full bracket → empty markets, no crash
    r = client.get("/api/bets/outrights?n=500&top=5")
    assert r.status_code == 200
    body = r.json()
    assert body["n"] == 0
    assert body["markets"]["champion"] == []
