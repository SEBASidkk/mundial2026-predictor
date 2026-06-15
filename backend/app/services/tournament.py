"""Monte Carlo tournament simulator (World Cup 2026 format).

48 teams in 12 groups of 4. Group winners + runners-up (24) plus the 8 best
third-placed teams advance to a 32-team single-elimination knockout
(R32 -> R16 -> QF -> SF -> Final).

Each match samples goals from independent Poisson(lambda) draws, with lambda
derived from team ELO (neutral venue, no home advantage). Knockout ties are
resolved by a penalty shootout modelled as an ELO-weighted coin flip.

Runs N full tournaments and reports, per team, the probability of reaching each
stage and winning the title.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List

import numpy as np
from sqlalchemy.orm import Session, joinedload

from app.models.match import Match
from app.models.team import Team
from pipeline.features.seed_ratings import strengths_from_elo


def _load_groups(db: Session) -> Dict[str, List[Team]]:
    matches = (
        db.query(Match)
        .options(joinedload(Match.home_team), joinedload(Match.away_team))
        .filter(Match.group.isnot(None))
        .all()
    )
    groups: Dict[str, set] = defaultdict(set)
    teams_by_id: Dict[int, Team] = {}
    for m in matches:
        groups[m.group].add(m.home_team_id)
        groups[m.group].add(m.away_team_id)
        teams_by_id[m.home_team_id] = m.home_team
        teams_by_id[m.away_team_id] = m.away_team
    return {g: [teams_by_id[tid] for tid in ids] for g, ids in groups.items()}


def _lambdas(att_a, def_a, att_b, def_b):
    """Goal rates for A vs B at a neutral venue."""
    return math.exp(att_a - def_b), math.exp(att_b - def_a)


def simulate_tournament(db: Session, n: int = 2000) -> Dict:
    groups = _load_groups(db)
    # Static per-team strengths + elo
    teams: Dict[int, Team] = {}
    strength: Dict[int, Dict[str, float]] = {}
    elo: Dict[int, float] = {}
    for g_teams in groups.values():
        for t in g_teams:
            teams[t.id] = t
            strength[t.id] = strengths_from_elo(t.elo_rating)
            elo[t.id] = t.elo_rating

    group_names = sorted(groups.keys())
    ids_by_group = {g: [t.id for t in groups[g]] for g in group_names}

    # Tally counters
    stages = ("r32", "r16", "qf", "sf", "final", "champion")
    counts: Dict[int, Dict[str, int]] = {tid: {s: 0 for s in stages} for tid in teams}
    group_winner: Dict[int, int] = {tid: 0 for tid in teams}

    rng = np.random.default_rng()

    def play(a: int, b: int):
        """Return (goals_a, goals_b)."""
        la, lb = _lambdas(strength[a]["attack"], strength[a]["defense"],
                          strength[b]["attack"], strength[b]["defense"])
        return int(rng.poisson(la)), int(rng.poisson(lb))

    def knockout(a: int, b: int) -> int:
        ga, gb = play(a, b)
        if ga > gb:
            return a
        if gb > ga:
            return b
        # Penalties: ELO-weighted coin flip
        pa = 1.0 / (1.0 + 10 ** ((elo[b] - elo[a]) / 400.0))
        return a if rng.random() < pa else b

    for _ in range(n):
        thirds = []  # (pts, gd, gf, tid)
        qualifiers_seed = []  # (seed_rank, pts, elo, tid)

        for g in group_names:
            tids = ids_by_group[g]
            stat = {tid: {"pts": 0, "gf": 0, "ga": 0} for tid in tids}
            # round robin
            for i in range(len(tids)):
                for j in range(i + 1, len(tids)):
                    a, b = tids[i], tids[j]
                    ga, gb = play(a, b)
                    stat[a]["gf"] += ga; stat[a]["ga"] += gb
                    stat[b]["gf"] += gb; stat[b]["ga"] += ga
                    if ga > gb:
                        stat[a]["pts"] += 3
                    elif gb > ga:
                        stat[b]["pts"] += 3
                    else:
                        stat[a]["pts"] += 1; stat[b]["pts"] += 1
            ranked = sorted(
                tids,
                key=lambda t: (stat[t]["pts"], stat[t]["gf"] - stat[t]["ga"], stat[t]["gf"], elo[t]),
                reverse=True,
            )
            group_winner[ranked[0]] += 1
            # 1st and 2nd qualify; 3rd into best-thirds pool
            qualifiers_seed.append((0, stat[ranked[0]]["pts"], elo[ranked[0]], ranked[0]))
            qualifiers_seed.append((1, stat[ranked[1]]["pts"], elo[ranked[1]], ranked[1]))
            t3 = ranked[2]
            thirds.append((stat[t3]["pts"], stat[t3]["gf"] - stat[t3]["ga"], stat[t3]["gf"], elo[t3], t3))

        # best 8 thirds
        thirds.sort(reverse=True)
        for pts, gd, gf, e, tid in thirds[:8]:
            qualifiers_seed.append((2, pts, e, tid))

        # Seed the 32-team bracket: group winners, then runners, then thirds;
        # within each tier by points then elo. Standard 1 vs 32 pairing.
        qualifiers_seed.sort(key=lambda x: (x[0], -x[1], -x[2]))
        bracket = [x[3] for x in qualifiers_seed][:32]
        for tid in bracket:
            counts[tid]["r32"] += 1

        # standard seeding: seed[i] vs seed[31-i]
        order = []
        for i in range(16):
            order.append(bracket[i])
            order.append(bracket[31 - i])

        round_names = ["r16", "qf", "sf", "final", "champion"]
        current = order
        for rname in round_names:
            nxt = []
            for k in range(0, len(current), 2):
                w = knockout(current[k], current[k + 1])
                counts[w][rname] += 1
                nxt.append(w)
            current = nxt

    # Build output
    out = []
    for tid, t in teams.items():
        c = counts[tid]
        out.append({
            "team": t.name,
            "elo": round(t.elo_rating),
            "group_winner": round(group_winner[tid] / n, 4),
            "reach_r16": round(c["r16"] / n, 4),
            "reach_qf": round(c["qf"] / n, 4),
            "reach_sf": round(c["sf"] / n, 4),
            "reach_final": round(c["final"] / n, 4),
            "champion": round(c["champion"] / n, 4),
        })
    out.sort(key=lambda x: x["champion"], reverse=True)
    return {"n": n, "teams": out}
