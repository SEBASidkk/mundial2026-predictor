"""Tests for credible intervals and fractional Kelly staking."""
import pytest

from app.services.safe_bets import credible_interval, kelly_fraction


def test_credible_interval_brackets_prob():
    lo, hi = credible_interval(0.6, n=10000)
    assert lo < 0.6 < hi
    assert 0.0 <= lo and hi <= 1.0


def test_credible_interval_narrows_with_more_sims():
    _, hi_small = credible_interval(0.5, n=100)
    _, hi_big = credible_interval(0.5, n=100000)
    assert (hi_big - 0.5) < (hi_small - 0.5)


def test_kelly_zero_when_no_edge():
    # fair odds = 1/p ⇒ no edge ⇒ no stake
    assert kelly_fraction(0.5, 2.0) == 0.0


def test_kelly_positive_when_value():
    # model 60% but odds imply 50% ⇒ positive edge ⇒ positive stake
    stake = kelly_fraction(0.6, 2.0)
    assert stake > 0.0


def test_kelly_capped():
    # huge edge must not exceed the cap
    assert kelly_fraction(0.95, 5.0, cap=0.10) <= 0.10


def test_kelly_zero_on_bad_odds():
    assert kelly_fraction(0.6, 1.0) == 0.0
