"""Tests for historical ingestion, data-driven ELO and the goals GBM."""
from datetime import date

import pytest

from pipeline.ingestion import historical as H
from pipeline.ingestion.historical import HistMatch, canonical
from pipeline.features.historical_elo import run_elo, recent_form
from pipeline.features.dc_fit import fit_from_history, save_dc_params, load_dc_params
from pipeline.models import goals_gbm
from pipeline.models.ensemble import second_opinion_1x2


def _m(y, home, away, hg, ag, tournament="Friendly", neutral=False):
    return HistMatch(date(y, 6, 1), home, away, hg, ag, tournament, neutral)


# ---- ingestion -------------------------------------------------------------
def test_canonical_maps_known_names():
    assert canonical("Czech Republic") == "Czechia"
    assert canonical("DR Congo") == "Congo DR"
    assert canonical("Brazil") == "Brazil"  # unmapped passthrough


def test_load_matches_parses_and_filters(tmp_path, monkeypatch):
    csv = tmp_path / "results.csv"
    csv.write_text(
        "date,home_team,away_team,home_score,away_score,tournament,city,country,neutral\n"
        "2020-01-01,Brazil,Cape Verde,3,0,Friendly,Rio,Brazil,FALSE\n"
        "2099-01-01,Spain,France,NA,NA,Friendly,Madrid,Spain,TRUE\n"  # future, dropped
    )
    monkeypatch.setattr(H, "CSV_PATH", csv)
    rows = H.load_matches()
    assert len(rows) == 1
    assert rows[0].home == "Brazil" and rows[0].away == "Cape Verde Islands"  # aliased
    assert rows[0].home_goals == 3 and not rows[0].neutral


def test_hist_match_weight_by_tournament():
    assert _m(2020, "A", "B", 1, 0, "FIFA World Cup").weight > _m(2020, "A", "B", 1, 0, "Friendly").weight


# ---- ELO -------------------------------------------------------------------
def test_run_elo_rewards_winners():
    matches = [_m(2000 + i, "Strong", "Weak", 3, 0) for i in range(10)]
    elos, rows = run_elo(matches)
    assert elos["Strong"] > 1500 > elos["Weak"]
    assert len(rows) == len(matches)
    # pre-match feature captured before the result (first game still at base)
    assert rows[0]["elo_home"] == pytest.approx(1500.0)


def test_recent_form_tracks_goals():
    matches = [_m(2000 + i, "A", "B", 2, 1) for i in range(6)]
    form = recent_form(matches)
    assert form["A"][0] == pytest.approx(2.0)   # A scores 2
    assert form["A"][1] == pytest.approx(1.0)   # A concedes 1


# ---- GBM -------------------------------------------------------------------
def _synth_rows(n=800):
    import random
    random.seed(1)
    rows = []
    for _ in range(n):
        eh = random.uniform(1500, 2100)
        ea = random.uniform(1500, 2100)
        # stronger team scores more, on average
        hg = max(0, round(random.gauss(1.3 + (eh - ea) / 400, 1)))
        ag = max(0, round(random.gauss(1.3 + (ea - eh) / 400, 1)))
        rows.append({
            "elo_home": eh, "elo_away": ea, "elo_diff": eh - ea, "neutral": 0,
            "home_gf": 1.4, "home_ga": 1.1, "away_gf": 1.3, "away_ga": 1.2,
            "home_goals": hg, "away_goals": ag,
        })
    return rows


def test_gbm_trains_and_favours_stronger_team():
    model = goals_gbm.train(_synth_rows())
    assert model is not None
    lam_h, lam_a = model.predict(2050, 1550, False, (1.5, 1.0), (1.0, 1.5))
    assert lam_h > lam_a  # strong home outscores weak away


def test_gbm_skips_when_too_few_rows():
    assert goals_gbm.train(_synth_rows(50)) is None


def test_second_opinion_falls_back_without_gbm():
    r = second_opinion_1x2(None, None, "A", "B", 2000, 1600)
    assert r["prob_home_win"] > r["prob_away_win"]
    assert abs(sum(r.values()) - 1.0) < 1e-6


# ---- DC fit ----------------------------------------------------------------
def test_fit_from_history_returns_params_for_connected_teams():
    teams = [chr(ord("A") + i) for i in range(8)]  # A..H (>= 8-team guard)
    wc = set(teams)
    name_to_ext = {t: i + 1 for i, t in enumerate(teams)}
    strong = {"A", "B", "C"}
    matches = []
    import itertools
    for y in range(2015, 2024):
        for h, a in itertools.permutations(teams, 2):
            hg = 2 if h in strong else 1
            ag = 2 if a in strong else 1
            matches.append(_m(y, h, a, hg, ag))
    params = fit_from_history(matches, wc, name_to_ext, since="2014-01-01", min_games=8)
    assert params is not None
    assert set(params["attack"]).issubset(set(name_to_ext.values()))
    assert "rho" in params


def test_dc_params_roundtrip(tmp_path, monkeypatch):
    import pipeline.features.dc_fit as D
    monkeypatch.setattr(D, "_DC_PATH", tmp_path / "dc.json")
    params = {"attack": {1: 0.5}, "defense": {1: 0.3}, "home_advantage": 0.2, "rho": -0.1}
    D.save_dc_params(params)
    loaded = D.load_dc_params()
    assert loaded["attack"][1] == 0.5   # keys restored as int
    assert loaded["rho"] == -0.1
