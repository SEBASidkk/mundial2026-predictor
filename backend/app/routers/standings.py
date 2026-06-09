from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict
from app.database import get_db
from app.models.match import Match
from app.models.team import Team

router = APIRouter()


@router.get("/standings")
def get_standings(db: Session = Depends(get_db)) -> Dict:
    teams = {
        t.id: {"name": t.name, "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}
        for t in db.query(Team).all()
    }

    for m in db.query(Match).filter(Match.played == True).all():
        h, a = m.home_team_id, m.away_team_id
        if h not in teams or a not in teams:
            continue
        teams[h]["P"] += 1
        teams[a]["P"] += 1
        teams[h]["GF"] += m.home_goals or 0
        teams[h]["GA"] += m.away_goals or 0
        teams[a]["GF"] += m.away_goals or 0
        teams[a]["GA"] += m.home_goals or 0
        if m.home_goals > m.away_goals:
            teams[h]["W"] += 1
            teams[h]["Pts"] += 3
            teams[a]["L"] += 1
        elif m.home_goals == m.away_goals:
            teams[h]["D"] += 1
            teams[h]["Pts"] += 1
            teams[a]["D"] += 1
            teams[a]["Pts"] += 1
        else:
            teams[a]["W"] += 1
            teams[a]["Pts"] += 3
            teams[h]["L"] += 1

    return {"standings": list(teams.values())}
