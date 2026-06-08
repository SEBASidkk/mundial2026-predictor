from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.team import Team
from app.models.match import Match
from app.models.player import Player
from app.models.prediction import Prediction


def get_test_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def test_all_tables_created():
    engine = get_test_engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "teams" in tables
    assert "matches" in tables
    assert "players" in tables
    assert "predictions" in tables


def test_team_insert():
    engine = get_test_engine()
    Session = sessionmaker(bind=engine)
    with Session() as session:
        team = Team(external_id=1, name="Brazil", country_code="BRA", elo_rating=2050.0)
        session.add(team)
        session.commit()
        result = session.query(Team).filter_by(external_id=1).first()
        assert result.name == "Brazil"
        assert result.elo_rating == 2050.0
