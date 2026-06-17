"""Real historical international results (martj42 dataset, 1872–present).

Source: https://github.com/martj42/international_results (results.csv, ~49k
matches). This is the data the model was missing — with it we fit ELOs, the
Dixon-Coles attack/defense and the gradient-boosted goals model from reality
instead of hand-seeded priors.

`ensure_dataset()` downloads the CSV on first use; everything else reads the
local copy. Historical team names are mapped onto our DB names so ELO/form
lookups line up with the 48 World Cup teams.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CSV_PATH = DATA_DIR / "results.csv"
SOURCE_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
)

# Historical dataset name -> our DB name (only the few that differ).
NAME_MAP = {
    "Czech Republic": "Czechia",
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "Cape Verde": "Cape Verde Islands",
    "DR Congo": "Congo DR",
}

# Rough tournament importance for ELO K-weighting (World Football Elo style).
TOURNAMENT_WEIGHT = {
    "FIFA World Cup": 60.0,
    "FIFA World Cup qualification": 40.0,
    "UEFA Euro": 50.0,
    "UEFA Euro qualification": 38.0,
    "Copa América": 50.0,
    "African Cup of Nations": 45.0,
    "AFC Asian Cup": 45.0,
    "UEFA Nations League": 40.0,
    "Confederations Cup": 45.0,
    "CONCACAF Championship": 40.0,
    "Gold Cup": 40.0,
    "Friendly": 20.0,
}
DEFAULT_WEIGHT = 30.0


def canonical(name: str) -> str:
    return NAME_MAP.get(name, name)


@dataclass
class HistMatch:
    date: date
    home: str
    away: str
    home_goals: int
    away_goals: int
    tournament: str
    neutral: bool

    @property
    def weight(self) -> float:
        return TOURNAMENT_WEIGHT.get(self.tournament, DEFAULT_WEIGHT)


def ensure_dataset() -> bool:
    """Download results.csv if missing. Returns True if the file is available."""
    if CSV_PATH.exists() and CSV_PATH.stat().st_size > 0:
        return True
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import requests

        log.info("Downloading historical results from %s", SOURCE_URL)
        resp = requests.get(SOURCE_URL, timeout=60)
        resp.raise_for_status()
        CSV_PATH.write_bytes(resp.content)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not download historical dataset: %s", exc)
        return False


def load_matches(since: Optional[str] = None) -> List[HistMatch]:
    """Played matches (chronological). `since` is an ISO date lower bound."""
    if not ensure_dataset():
        return []
    import csv

    lo = datetime.fromisoformat(since).date() if since else None
    out: List[HistMatch] = []
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            hs, as_ = row["home_score"], row["away_score"]
            if hs in ("", "NA") or as_ in ("", "NA"):
                continue  # unplayed / future fixture
            try:
                d = datetime.fromisoformat(row["date"]).date()
            except ValueError:
                continue
            if lo and d < lo:
                continue
            out.append(HistMatch(
                date=d,
                home=canonical(row["home_team"]),
                away=canonical(row["away_team"]),
                home_goals=int(float(hs)),
                away_goals=int(float(as_)),
                tournament=row["tournament"],
                neutral=str(row["neutral"]).strip().lower() == "true",
            ))
    out.sort(key=lambda m: m.date)
    log.info("Loaded %d historical matches%s", len(out), f" since {since}" if since else "")
    return out
