"""Tests for robust odds team-name matching (aliases + fuzzy)."""
from types import SimpleNamespace

from pipeline.ingestion.odds_api import _norm, _best_fuzzy, map_events_to_matches


def _match(mid, home, away):
    return SimpleNamespace(
        id=mid,
        home_team=SimpleNamespace(name=home),
        away_team=SimpleNamespace(name=away),
    )


def test_norm_applies_alias():
    assert _norm("USA") == _norm("United States")
    assert _norm("Korea Republic") == _norm("South Korea")
    assert _norm("Türkiye") == _norm("Turkey")


def test_fuzzy_matches_close_spelling():
    cands = ["unitedstates", "southkorea", "brazil"]
    assert _best_fuzzy("unitedstate", cands) == "unitedstates"
    assert _best_fuzzy("zzzzzz", cands) is None


def test_map_events_matches_via_alias():
    matches = [_match(10, "United States", "Mexico")]
    events = [{
        "home_team": "USA", "away_team": "Mexico",
        "bookmakers": [{
            "title": "Pinnacle",
            "markets": [{"key": "h2h", "outcomes": [
                {"name": "USA", "price": 2.1},
                {"name": "Mexico", "price": 3.0},
                {"name": "Draw", "price": 3.2},
            ]}],
        }],
    }]
    rows = map_events_to_matches(events, matches)
    assert rows
    assert all(r["match_id"] == 10 for r in rows)
    assert any(r["selection"] == "home" for r in rows)


def test_map_events_skips_unknown_teams():
    matches = [_match(10, "Brazil", "Argentina")]
    events = [{"home_team": "Narnia", "away_team": "Atlantis", "bookmakers": []}]
    assert map_events_to_matches(events, matches) == []
