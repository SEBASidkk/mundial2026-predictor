"""The Odds API ingestion — real bookmaker odds for World Cup matches.

Docs: https://the-odds-api.com/liveapi/guides/v4/

If no ODDS_API_KEY is configured, fetch_odds() returns [] and the rest of the
app falls back to fair odds (1 / model probability). The pipeline never fails
because real odds are unavailable.
"""
import time
import logging
import unicodedata
from difflib import SequenceMatcher
from datetime import datetime
from typing import Dict, List, Optional

import requests

from app.config import settings

log = logging.getLogger(__name__)

BASE_URL = "https://api.the-odds-api.com/v4"
SPORT_KEY = "soccer_fifa_world_cup"

# Canonical name aliases — bookmakers and the fixtures API disagree on national
# team names. Keys/values are normalised on use, so write them naturally.
TEAM_ALIASES: Dict[str, str] = {
    "usa": "united states",
    "us": "united states",
    "united states of america": "united states",
    "korea republic": "south korea",
    "republic of korea": "south korea",
    "korea dpr": "north korea",
    "ir iran": "iran",
    "iran islamic republic": "iran",
    "czechia": "czech republic",
    "turkiye": "turkey",
    "cote divoire": "ivory coast",
    "china pr": "china",
    "bosnia herzegovina": "bosnia and herzegovina",
    "cabo verde": "cape verde",
    "drc": "dr congo",
    "congo dr": "dr congo",
}

# Minimum similarity for a fuzzy name match before we give up and skip.
_FUZZY_THRESHOLD = 0.84


def _norm(name: str) -> str:
    """Normalize a team name for matching: lowercase, strip accents/punctuation,
    then collapse through the alias table."""
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    cleaned = "".join(c for c in s.lower() if c.isalnum() or c == " ").strip()
    aliased = TEAM_ALIASES.get(cleaned, cleaned)
    return aliased.replace(" ", "")


def _best_fuzzy(target: str, candidates: List[str]) -> Optional[str]:
    """Closest candidate name to `target` above the similarity threshold."""
    best, best_score = None, 0.0
    for c in candidates:
        score = SequenceMatcher(None, target, c).ratio()
        if score > best_score:
            best, best_score = c, score
    return best if best_score >= _FUZZY_THRESHOLD else None


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
    all_team_norms = sorted({n for pair in by_teams for n in pair})

    out: List[Dict] = []
    matched = 0
    unmatched: List[str] = []
    for ev in events:
        h, a = ev.get("home_team", ""), ev.get("away_team", "")
        hn, an = _norm(h), _norm(a)
        m = by_teams.get((hn, an))
        if m is None:
            # Fuzzy fallback: tolerate spelling drift the alias table missed.
            hf = _best_fuzzy(hn, all_team_norms)
            af = _best_fuzzy(an, all_team_norms)
            if hf and af:
                m = by_teams.get((hf, af))
        if m is None:
            unmatched.append(f"{h} vs {a}")
            continue
        matched += 1
        for row in normalize_event_odds(ev, h, a):
            out.append({"match_id": m.id, **row})
    log.info(f"Odds API: matched {matched}/{len(events)} events to DB matches, {len(out)} odds rows")
    if unmatched:
        log.warning("Odds API: %d events unmatched (review aliases): %s",
                    len(unmatched), "; ".join(unmatched[:10]))
    return out
