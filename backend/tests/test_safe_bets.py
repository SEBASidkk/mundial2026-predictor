"""Unit tests for the simulation-backed safe-bets engine (pure functions)."""
import numpy as np
import pytest

from app.services.safe_bets import (
    simulate_markets,
    safety_score,
    build_parlay,
    diversify_by_market,
    build_rationale,
    MARKET_LABELS,
)


def test_simulate_markets_keys_and_range():
    rng = np.random.default_rng(42)
    probs = simulate_markets(1.4, 1.1, n=5000, rng=rng)
    # every advertised market/selection is present
    expected = {
        ("1x2", "home"), ("1x2", "draw"), ("1x2", "away"),
        ("over_15", "over"), ("over_25", "over"), ("over_35", "over"),
        ("under_25", "under"), ("under_35", "under"),
        ("btts", "yes"), ("btts", "no"),
    }
    assert expected.issubset(set(probs.keys()))
    for v in probs.values():
        assert 0.0 <= v <= 1.0


def test_simulate_markets_1x2_normalised():
    rng = np.random.default_rng(7)
    p = simulate_markets(1.5, 1.0, n=20000, rng=rng)
    s = p[("1x2", "home")] + p[("1x2", "draw")] + p[("1x2", "away")]
    assert s == pytest.approx(1.0, abs=1e-9)


def test_simulate_markets_favours_stronger_side():
    rng = np.random.default_rng(1)
    p = simulate_markets(2.4, 0.6, n=20000, rng=rng)
    assert p[("1x2", "home")] > p[("1x2", "away")]
    # over/under consistency: over_25 + under_25 == 1 (no exactly-2.5 goals)
    assert p[("over_25", "over")] + p[("under_25", "under")] == pytest.approx(1.0, abs=1e-9)


def test_btts_complement():
    rng = np.random.default_rng(99)
    p = simulate_markets(1.2, 1.2, n=20000, rng=rng)
    assert p[("btts", "yes")] + p[("btts", "no")] == pytest.approx(1.0, abs=1e-9)


def test_safety_score_monotonic_in_prob():
    assert safety_score(0.8, 0.0, 0.9) > safety_score(0.6, 0.0, 0.9)


def test_safety_score_rewards_positive_edge():
    assert safety_score(0.7, 0.10, 0.9) > safety_score(0.7, 0.0, 0.9)


def test_safety_score_ignores_negative_edge():
    # a bet priced against us shouldn't be penalised below its base probability term
    assert safety_score(0.7, -0.20, 0.9) == safety_score(0.7, 0.0, 0.9)


def test_market_labels_cover_simulated_markets():
    rng = np.random.default_rng(3)
    p = simulate_markets(1.0, 1.0, n=1000, rng=rng)
    for market, _selection in p:
        assert market in MARKET_LABELS


def _pick(match_id, prob, odds, safety):
    return {
        "match_id": match_id,
        "model_prob": prob,
        "decimal_odds": odds,
        "safety_score": safety,
        "label": f"pick-{match_id}",
        "home_team": "H", "away_team": "A",
    }


def test_build_parlay_joint_probability_and_odds():
    picks = [
        _pick(1, 0.80, 1.25, 0.8),
        _pick(2, 0.70, 1.43, 0.7),
        _pick(3, 0.60, 1.67, 0.6),
    ]
    parlay = build_parlay(picks, legs=2)
    assert len(parlay["legs"]) == 2
    # top-2 by safety = matches 1 and 2
    assert parlay["combined_prob"] == pytest.approx(0.80 * 0.70, abs=1e-9)
    assert parlay["combined_odds"] == pytest.approx(1.25 * 1.43, abs=1e-2)


def test_build_parlay_one_leg_per_match():
    picks = [
        _pick(1, 0.80, 1.25, 0.9),
        _pick(1, 0.65, 1.54, 0.85),  # same match, must be skipped
        _pick(2, 0.70, 1.43, 0.7),
    ]
    parlay = build_parlay(picks, legs=3)
    match_ids = [leg["match_id"] for leg in parlay["legs"]]
    assert match_ids == [1, 2]  # only two distinct matches available


def test_build_parlay_expected_value_sign():
    # fair-priced legs (odds == 1/prob) => EV ~ 0
    picks = [_pick(1, 0.5, 2.0, 0.5), _pick(2, 0.5, 2.0, 0.5)]
    parlay = build_parlay(picks, legs=2)
    assert parlay["expected_value"] == pytest.approx(0.0, abs=1e-6)


def test_build_parlay_empty():
    assert build_parlay([], legs=3)["legs"] == []


def _full_pick(**over):
    base = {
        "match_id": 1, "home_team": "Argentina", "away_team": "Austria",
        "market": "1x2", "selection": "home", "model_prob": 0.75,
        "decimal_odds": 1.70, "implied_prob": 0.588, "edge": 0.162,
        "source": "market", "bookmaker": "GTbets", "model_confidence": 0.79,
        "exp_goals_total": 2.8,
    }
    base.update(over)
    return base


def test_rationale_mentions_probability_and_value():
    text = build_rationale(_full_pick())
    assert "75%" in text
    assert "GTbets" in text
    assert "valor" in text.lower()
    assert "Argentina" in text


def test_rationale_over_mentions_expected_goals():
    text = build_rationale(_full_pick(market="over_25", selection="over"))
    assert "2.8" in text
    assert "goles" in text.lower()


def test_rationale_fair_odds_when_no_bookmaker():
    text = build_rationale(_full_pick(source="fair", bookmaker=None, edge=0.0))
    assert "momio justo" in text.lower()


def test_rationale_no_extra_value_when_edge_negative():
    text = build_rationale(_full_pick(edge=-0.05))
    assert "sin valor" in text.lower()


def _mk(market, score, match_id):
    return {"market": market, "safety_score": score, "match_id": match_id}


def test_diversify_caps_dominant_market():
    # 10 Under 3.5 (all high, distinct matches) + 2 of other markets
    picks = [_mk("under_35", 0.80 - i * 0.001, i) for i in range(10)]
    picks += [_mk("1x2", 0.70, 100), _mk("btts", 0.66, 101)]
    picks.sort(key=lambda x: x["safety_score"], reverse=True)
    # limit reachable within the cap → no backfill needed, cap holds
    out = diversify_by_market(picks, limit=4, max_per_market=2)
    markets = [p["market"] for p in out]
    assert markets.count("under_35") <= 2          # capped
    assert "1x2" in markets and "btts" in markets   # variety surfaced


def test_diversify_caps_per_match():
    # one match offering many strong markets shouldn't monopolise the board when
    # other fixtures are available to fill the limit
    picks = [_mk(m, 0.80 - i * 0.01, 7) for i, m in enumerate(
        ["under_35", "over_15", "1x2", "btts", "under_25"])]
    picks += [_mk("1x2", 0.70, 1), _mk("1x2", 0.69, 2), _mk("1x2", 0.68, 3)]
    picks.sort(key=lambda x: x["safety_score"], reverse=True)
    out = diversify_by_market(picks, limit=4, max_per_market=5, max_per_match=2)
    from_match_7 = [p for p in out if p["match_id"] == 7]
    assert len(from_match_7) == 2          # capped, others fill the rest
    assert {p["match_id"] for p in out} >= {7, 1, 2}


def test_diversify_backfills_to_limit():
    picks = [_mk("under_35", 0.80 - i * 0.001, i) for i in range(10)]
    picks.sort(key=lambda x: x["safety_score"], reverse=True)
    # only one market available; backfill must still reach the limit
    out = diversify_by_market(picks, limit=5, max_per_market=2)
    assert len(out) == 5
