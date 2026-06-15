"""Static seed ELO ratings for World Cup teams.

The free football-data.org tier does not expose historical match results, so the
ELO feature and Dixon-Coles fit have no data to differentiate teams (every team
stays at 1500 and every match gets identical predictions).

These approximate world-football ELO ratings give the model a realistic, varied
prior so predictions, markets and bets differ per fixture. They are used ONLY as
a fallback when no historical matches are ingested; real results override them.
"""
from typing import Dict
from sqlalchemy.orm import Session

from app.models.team import Team

# Approximate world-football ELO ratings (rough, ~2026). Keyed by football-data
# team name. Unknown teams fall back to DEFAULT_ELO.
SEED_ELO: Dict[str, float] = {
    "Argentina": 2090, "France": 2075, "Spain": 2065, "England": 2005,
    "Brazil": 2010, "Portugal": 1980, "Netherlands": 1965, "Germany": 1955,
    "Belgium": 1935, "Croatia": 1925, "Uruguay": 1895, "Colombia": 1880,
    "Morocco": 1865, "Switzerland": 1830, "Japan": 1830, "Senegal": 1810,
    "Mexico": 1815, "United States": 1800, "Austria": 1800, "Norway": 1790,
    "Ecuador": 1790, "Iran": 1775, "South Korea": 1780, "Turkey": 1790,
    "Sweden": 1770, "Scotland": 1760, "Algeria": 1760, "Czechia": 1760,
    "Australia": 1760, "Egypt": 1745, "Ivory Coast": 1740, "Canada": 1740,
    "Bosnia-Herzegovina": 1730, "Paraguay": 1720, "Tunisia": 1710,
    "Ghana": 1700, "Congo DR": 1700, "Saudi Arabia": 1685, "Qatar": 1680,
    "Uzbekistan": 1680, "South Africa": 1680, "Iraq": 1660, "Panama": 1660,
    "Cape Verde Islands": 1655, "Jordan": 1640, "New Zealand": 1620,
    "Haiti": 1585, "Curaçao": 1560,
}

DEFAULT_ELO = 1700.0


def seed_team_elos(db: Session) -> int:
    """Set each team's elo_rating from SEED_ELO (fallback DEFAULT_ELO). Returns count."""
    teams = db.query(Team).all()
    for t in teams:
        t.elo_rating = SEED_ELO.get(t.name, DEFAULT_ELO)
    db.commit()
    return len(teams)


def strengths_from_elo(elo: float, k: float = 0.45) -> Dict[str, float]:
    """Derive Dixon-Coles attack/defense offsets from an ELO rating.

    s = (elo - 1500) / 400 maps ratings to roughly [-0.35, +1.5]. Stronger teams
    attack more (higher att) and concede less (higher def, which is subtracted
    from the opponent's goal rate).
    """
    s = (elo - 1500.0) / 400.0
    return {"attack": 0.10 + k * s, "defense": 0.10 + k * s}
