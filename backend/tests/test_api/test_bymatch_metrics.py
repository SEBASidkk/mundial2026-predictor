"""API tests for /bets/by-match (chronological per-match picks) and
/model/metrics (backtest)."""
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.team import Team
from app.models.match import Match
from app.models.prediction import Prediction

TEST_DB = "sqlite:///./test_bymatch.db"
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


def _upcoming(db, mid, h, a, lam_h, lam_a, when):
    db.add(Match(
        id=mid, external_id=mid, home_team_id=h, away_team_id=a,
        kickoff_utc=when, stage="GROUP_STAGE", group="A",
        venue_city="Dallas", played=False,
    ))
    db.add(Prediction(
        match_id=mid, prob_home_win=0.6, prob_draw=0.25, prob_away_win=0.15,
        lambda_home=lam_h, lambda_away=lam_a, score_matrix={}, model_confidence=0.8,
    ))


def setup_function():
    _prev["ov"] = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    db.add_all([
        Team(id=1, external_id=1, name="Brazil", country_code="BRA", elo_rating=2050.0),
        Team(id=2, external_id=2, name="Bolivia", country_code="BOL", elo_rating=1500.0),
        Team(id=3, external_id=3, name="France", country_code="FRA", elo_rating=2030.0),
        Team(id=4, external_id=4, name="Panama", country_code="PAN", elo_rating=1550.0),
    ])
    # Seed out of chronological order to prove the endpoint sorts.
    _upcoming(db, 2, 3, 4, 2.2, 0.6, datetime(2026, 6, 22, 18, 0))
    _upcoming(db, 1, 1, 2, 2.4, 0.5, datetime(2026, 6, 20, 18, 0))
    # A played match so /model/metrics has data.
    db.add(Match(
        id=3, external_id=3, home_team_id=1, away_team_id=2,
        kickoff_utc=datetime(2026, 6, 18, 18, 0), stage="GROUP_STAGE", group="A",
        venue_city="Dallas", played=True, home_goals=3, away_goals=0,
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


def test_by_match_is_chronological_and_carries_best_pick():
    r = client.get("/api/bets/by-match?n=3000")
    assert r.status_code == 200
    body = r.json()
    matches = body["matches"]
    assert len(matches) == 2
    # sorted by kickoff ascending
    kickoffs = [m["kickoff_utc"] for m in matches]
    assert kickoffs == sorted(kickoffs)
    first = matches[0]
    assert first["match_id"] == 1   # the 2026-06-20 fixture comes first
    assert first["home_code"] == "BRA"
    assert isinstance(first["picks"], list) and len(first["picks"]) >= 1
    # picks deduped by market family — no two share the goals family
    families = [
        "goals" if (p["market"].startswith("over") or p["market"].startswith("under"))
        else p["market"]
        for p in first["picks"]
    ]
    assert len(families) == len(set(families))
    pick = first["picks"][0]
    for field in ("label", "model_prob", "safety_score", "rationale",
                  "prob_ci_low", "prob_ci_high", "kelly_fraction"):
        assert field in pick
    assert len(pick["rationale"]) > 10


def test_model_metrics_returns_scores():
    r = client.get("/api/model/metrics")
    assert r.status_code == 200
    body = r.json()
    assert body["n"] >= 1
    assert 0.0 <= body["brier"] <= 2.0
    assert body["log_loss"] >= 0.0
    assert 0.0 <= body["accuracy"] <= 1.0
    assert "reliability" in body
    assert "calibration" in body
