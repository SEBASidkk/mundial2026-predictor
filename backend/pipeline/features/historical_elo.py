"""Data-driven ELO ratings and per-match features from real history.

Runs a World-Football-Elo-style rating over every historical international
match in chronological order. Two outputs from one pass:

  * `elos`         — each team's current rating (drives Dixon-Coles strengths),
  * `feature_rows` — for every match, the PRE-match ratings and recent form,
                     used (leak-free) to train the gradient-boosted goals model.

The K-factor is the tournament weight (World Cup matches move ratings more than
friendlies) scaled by a goal-difference multiplier, the standard approach.
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque, Dict, List, Tuple

from pipeline.ingestion.historical import HistMatch

BASE_ELO = 1500.0
HOME_FIELD = 65.0          # ELO points of home advantage (0 at neutral venues)
FORM_WINDOW = 5


def _goal_multiplier(goal_diff: int) -> float:
    g = abs(goal_diff)
    if g <= 1:
        return 1.0
    if g == 2:
        return 1.5
    if g == 3:
        return 1.75
    return 1.75 + (g - 3) / 8.0


def _expected(elo_home: float, elo_away: float, neutral: bool) -> float:
    hfa = 0.0 if neutral else HOME_FIELD
    return 1.0 / (1.0 + 10 ** (-(elo_home + hfa - elo_away) / 400.0))


def run_elo(matches: List[HistMatch]) -> Tuple[Dict[str, float], List[Dict]]:
    """Chronological ELO pass. Returns (final_elos, feature_rows)."""
    elos: Dict[str, float] = defaultdict(lambda: BASE_ELO)
    gf_hist: Dict[str, Deque[int]] = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
    ga_hist: Dict[str, Deque[int]] = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
    rows: List[Dict] = []

    def form(team: str) -> Tuple[float, float]:
        gf, ga = gf_hist[team], ga_hist[team]
        avg_gf = sum(gf) / len(gf) if gf else 1.2
        avg_ga = sum(ga) / len(ga) if ga else 1.2
        return avg_gf, avg_ga

    for m in matches:
        eh, ea = elos[m.home], elos[m.away]
        h_gf, h_ga = form(m.home)
        a_gf, a_ga = form(m.away)

        # Feature row captured BEFORE the match (pre-match state — no leakage).
        rows.append({
            "elo_home": eh, "elo_away": ea, "elo_diff": eh - ea,
            "neutral": 1 if m.neutral else 0,
            "home_gf": h_gf, "home_ga": h_ga, "away_gf": a_gf, "away_ga": a_ga,
            "home_goals": m.home_goals, "away_goals": m.away_goals,
        })

        # ELO update.
        we = _expected(eh, ea, m.neutral)
        if m.home_goals > m.away_goals:
            w = 1.0
        elif m.home_goals == m.away_goals:
            w = 0.5
        else:
            w = 0.0
        k = m.weight * _goal_multiplier(m.home_goals - m.away_goals)
        change = k * (w - we)
        elos[m.home] = eh + change
        elos[m.away] = ea - change

        gf_hist[m.home].append(m.home_goals); ga_hist[m.home].append(m.away_goals)
        gf_hist[m.away].append(m.away_goals); ga_hist[m.away].append(m.home_goals)

    return dict(elos), rows


def recent_form(matches: List[HistMatch]) -> Dict[str, Tuple[float, float]]:
    """Each team's last-`FORM_WINDOW` goals for/against averages (for prediction)."""
    gf: Dict[str, Deque[int]] = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
    ga: Dict[str, Deque[int]] = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
    for m in matches:
        gf[m.home].append(m.home_goals); ga[m.home].append(m.away_goals)
        gf[m.away].append(m.away_goals); ga[m.away].append(m.home_goals)
    out: Dict[str, Tuple[float, float]] = {}
    for team in set(gf) | set(ga):
        g, a = gf[team], ga[team]
        out[team] = (sum(g) / len(g) if g else 1.2, sum(a) / len(a) if a else 1.2)
    return out
