import httpx
from typing import List, Dict
from app.config import settings

BASE_URL = "https://api.football-data.org/v4"


def _headers() -> Dict:
    return {"X-Auth-Token": settings.football_data_api_key}


def fetch_world_cup_teams() -> List[Dict]:
    url = f"{BASE_URL}/competitions/WC/teams"
    resp = httpx.get(url, headers=_headers(), timeout=15)
    resp.raise_for_status()
    return [
        {
            "external_id": t["id"],
            "name": t["name"],
            "short_name": t.get("shortName"),
            "country_code": t.get("tla"),
        }
        for t in resp.json().get("teams", [])
    ]


def fetch_world_cup_matches() -> List[Dict]:
    url = f"{BASE_URL}/competitions/WC/matches"
    resp = httpx.get(url, headers=_headers(), timeout=15)
    resp.raise_for_status()
    matches = []
    for m in resp.json().get("matches", []):
        score = m.get("score", {}).get("fullTime", {})
        matches.append({
            "external_id": m["id"],
            "home_external_id": m["homeTeam"]["id"],
            "away_external_id": m["awayTeam"]["id"],
            "kickoff_utc": m["utcDate"],
            "stage": m.get("stage"),
            "group": m.get("group"),
            "venue": m.get("venue"),
            "home_goals": score.get("home"),
            "away_goals": score.get("away"),
            "status": m.get("status"),
        })
    return matches


def fetch_historical_matches(competition: str = "WC", seasons: List[int] = None) -> List[Dict]:
    if seasons is None:
        seasons = [2018, 2022]
    all_matches = []
    for season in seasons:
        url = f"{BASE_URL}/competitions/{competition}/matches?season={season}"
        try:
            resp = httpx.get(url, headers=_headers(), timeout=15)
        except Exception:
            continue
        if resp.status_code != 200:
            continue
        for m in resp.json().get("matches", []):
            score = m.get("score", {}).get("fullTime", {})
            if score.get("home") is not None:
                all_matches.append({
                    "home_id": m["homeTeam"]["id"],
                    "away_id": m["awayTeam"]["id"],
                    "home_goals": score["home"],
                    "away_goals": score["away"],
                    "competition": competition,
                    "date": m.get("utcDate"),
                })
    return all_matches
