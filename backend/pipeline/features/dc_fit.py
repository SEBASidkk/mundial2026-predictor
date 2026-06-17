"""Fit Dixon-Coles attack/defense from real recent matches.

Fits the Dixon-Coles MLE on recent internationals played *between World Cup
teams* (a small, well-connected graph that estimates cleanly and quickly).
Teams with too few games in the window are left out and fall back to their
ELO-derived strength at prediction time, so a rarely-seen side (e.g. Curaçao)
never gets a noisy, over-fit rating.

Returned attack/defense are keyed by the team's football-data external_id so
they slot straight into the existing `team_base_lambdas` path. The fitted
home_advantage is kept only for completeness — prediction overrides it with the
host-aware edge.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Set

from pipeline.ingestion.historical import HistMatch
from pipeline.models.dixon_coles import fit_dixon_coles

log = logging.getLogger(__name__)

_DC_PATH = Path(__file__).resolve().parents[2] / "dc_params.json"


def save_dc_params(dc_params: Dict) -> None:
    """Persist fitted attack/defense (keyed by external_id) for the backtest."""
    try:
        _DC_PATH.write_text(json.dumps({
            "attack": {str(k): v for k, v in dc_params["attack"].items()},
            "defense": {str(k): v for k, v in dc_params["defense"].items()},
            "home_advantage": dc_params.get("home_advantage", 0.3),
            "rho": dc_params.get("rho", -0.1),
        }))
    except OSError as exc:  # noqa: BLE001
        log.warning("Could not persist DC params: %s", exc)


def load_dc_params() -> Optional[Dict]:
    try:
        d = json.loads(_DC_PATH.read_text())
        return {
            "attack": {int(k): v for k, v in d["attack"].items()},
            "defense": {int(k): v for k, v in d["defense"].items()},
            "home_advantage": d.get("home_advantage", 0.3),
            "rho": d.get("rho", -0.1),
        }
    except (OSError, ValueError, KeyError):
        return None


def fit_from_history(
    matches: List[HistMatch],
    wc_names: Set[str],
    name_to_ext: Dict[str, int],
    since: str = "2014-01-01",
    min_games: int = 8,
) -> Optional[Dict]:
    """Fit DC on recent WC-vs-WC matches. Returns dc_params keyed by external_id."""
    from datetime import date

    lo = date.fromisoformat(since)
    pool = [
        m for m in matches
        if m.date >= lo and m.home in wc_names and m.away in wc_names
    ]
    if len(pool) < 50:
        log.warning("Only %d WC-vs-WC matches since %s — skipping DC fit.", len(pool), since)
        return None

    games = Counter()
    for m in pool:
        games[m.home] += 1
        games[m.away] += 1
    kept = {t for t, c in games.items() if c >= min_games}
    pool = [m for m in pool if m.home in kept and m.away in kept]
    if len(pool) < 50 or len(kept) < 8:
        log.warning("Too sparse after min_games filter (%d matches, %d teams).", len(pool), len(kept))
        return None

    names = sorted(kept)
    idx = {n: i for i, n in enumerate(names)}
    fit_matches = [{
        "home_id": idx[m.home], "away_id": idx[m.away],
        "home_goals": m.home_goals, "away_goals": m.away_goals,
    } for m in pool]

    raw = fit_dixon_coles(fit_matches)

    # Translate index-keyed params to external_id for WC teams we can map.
    attack: Dict[int, float] = {}
    defense: Dict[int, float] = {}
    for name, i in idx.items():
        ext = name_to_ext.get(name)
        if ext is None:
            continue
        attack[ext] = raw["attack"][i]
        defense[ext] = raw["defense"][i]

    log.info("Fitted Dixon-Coles on %d matches, %d teams (%d mapped to WC).",
             len(pool), len(kept), len(attack))
    return {
        "attack": attack,
        "defense": defense,
        "home_advantage": raw["home_advantage"],
        "rho": raw["rho"],
    }
