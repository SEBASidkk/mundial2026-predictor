"""The Odds API ingestion — real bookmaker odds for World Cup matches.

Docs: https://the-odds-api.com/liveapi/guides/v4/

If no ODDS_API_KEY is configured, fetch_odds() returns [] and the rest of the
app falls back to fair odds (1 / model probability). The pipeline never fails
because real odds are unavailable.
"""
import time
import logging
import unicodedata
from datetime import datetime
from typing import Dict, List

import requests

from app.config import settings

log = logging.getLogger(__name__)

BASE_URL = "https://api.the-odds-api.com/v4"
SPORT_KEY = "soccer_fifa_world_cup"


def _norm(name: str) -> str:
    """Normalize a team name for matching: lowercase, strip accents/punctuation."""
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s.lower() if c.isalnum())


def _get(url: str, params: Dict, retries: int = 5) -> requests.Response:
    last = None
    for attempt in range(retries):
        try:
            with requests.Session() as s:
                return s.get(url, params=params, headers={"Connection": "close"}, timeout=20)
        except requests.exceptions.RequestException as exc:
            last = exc
            time.sleep(min(20, 2 * (attempt + 1)))
    raise last


def fetch_odds() -> List[Dict]:
    """Raw odds events from The Odds API, or [] if no key / on failure."""
    if not settings.odds_api_key:
        log.info("ODDS_API_KEY not set — skipping real odds, using fair odds.")
        return []
    url = f"{BASE_URL}/sports/{SPORT_KEY}/odds"
    params = {
        "apiKey": settings.odds_api_key,
        "regions": "us,eu,uk",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
    }
    try:
        resp = _get(url, params)
    except Exception as exc:  # noqa: BLE001
        log.warning(f"Odds API request failed: {exc}")
        return []
    if resp.status_code != 200:
        log.warning(f"Odds API returned {resp.status_code}: {resp.text[:200]}")
        return []
    return resp.json()


def _best_decimal(outcomes_by_book: List[Dict]) -> Dict:
    """Pick the best (highest) decimal odd per outcome across bookmakers."""
    best: Dict[str, Dict] = {}
    for book_name, outcome in outcomes_by_book:
        name = outcome["name"]
        price = outcome.get("price")
        if price is None:
            continue
        if name not in best or price > best[name]["price"]:
            best[name] = {"price": price, "book": book_name}
    return best


def normalize_event_odds(event: Dict, home_name: str, away_name: str) -> List[Dict]:
    """Convert one Odds API event into our (market, selection, decimal, book) rows.

    Markets produced: 1x2 (home/draw/away), over_25/under_25 (totals at 2.5).
    """
    h2h_outcomes, totals_outcomes = [], []
    for book in event.get("bookmakers", []):
        bname = book.get("title") or book.get("key")
        for market in book.get("markets", []):
            key = market.get("key")
            for oc in market.get("outcomes", []):
                if key == "h2h":
                    h2h_outcomes.append((bname, oc))
                elif key == "totals" and abs((oc.get("point") or 0) - 2.5) < 1e-6:
                    totals_outcomes.append((bname, oc))

    rows: List[Dict] = []

    h2h_best = _best_decimal(h2h_outcomes)
    name_to_sel = {home_name: "home", away_name: "away", "Draw": "draw"}
    for oc_name, info in h2h_best.items():
        sel = name_to_sel.get(oc_name)
        if sel:
            rows.append({"market": "1x2", "selection": sel,
                         "decimal_odds": info["price"], "bookmaker": info["book"]})

    totals_best = _best_decimal(totals_outcomes)
    for oc_name, info in totals_best.items():
        sel = "over" if oc_name.lower().startswith("over") else "under"
        market = "over_25" if sel == "over" else "under_25"
        rows.append({"market": market, "selection": sel,
                     "decimal_odds": info["price"], "bookmaker": info["book"]})

    return rows


def map_events_to_matches(events: List[Dict], matches) -> List[Dict]:
    """Match Odds API events to our Match rows by team names (+ same kickoff day).

    Returns a flat list of dicts ready to upsert into the Odds table:
        {match_id, market, selection, decimal_odds, bookmaker}
    """
    # index our matches by (home_norm, away_norm)
    by_teams: Dict = {}
    for m in matches:
        by_teams[(_norm(m.home_team.name), _norm(m.away_team.name))] = m

    out: List[Dict] = []
    matched = 0
    for ev in events:
        h, a = ev.get("home_team", ""), ev.get("away_team", "")
        m = by_teams.get((_norm(h), _norm(a)))
        if m is None:
            continue
        matched += 1
        for row in normalize_event_odds(ev, h, a):
            out.append({"match_id": m.id, **row})
    log.info(f"Odds API: matched {matched}/{len(events)} events to DB matches, {len(out)} odds rows")
    return out
