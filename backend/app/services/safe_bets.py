"""Simulation-backed "safest bets" engine.

For every upcoming match this runs a vectorised Monte Carlo (sampling scorelines
from the ensemble Poisson goal rates stored on each prediction), derives the
empirical probability of every market from those simulations, attaches a real
bookmaker odd when available (fair odd otherwise), and ranks selections by a
composite *safety score* that rewards:

  * high model probability        (most likely to hit),
  * model confidence              (agreement between the blended models),
  * positive value edge           (model thinks the odd pays more than fair).

It also assembles accumulators (parlays) from independent single-match picks.

"Safe" here means *statistically strongest*, never *guaranteed* — no football
bet is risk-free, and the engine is explicit about probabilities and edges
rather than implying certainty.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session, joinedload

from app.models.match import Match
from app.models.odds import Odds
from app.models.prediction import Prediction
from app.services.bets import _fair_odds, _odds_index
from app.services.tournament import simulate_tournament

# Selection band: trivial near-locks (Over 0.5) and extreme longshots add no
# signal to a "safest bets" board.
DEFAULT_MIN_PROB = 0.55
DEFAULT_MAX_PROB = 0.97

# Over/Under near-certainties to drop from the cross-match leaderboard (kept in
# per-match detail). They would otherwise flood the board with identical rows.
TRIVIAL_MARKETS = {"over_05", "under_45"}

MARKET_LABELS: Dict[str, str] = {
    "1x2": "Resultado 1X2",
    "over_05": "Over 0.5 goles",
    "over_15": "Over 1.5 goles",
    "over_25": "Over 2.5 goles",
    "over_35": "Over 3.5 goles",
    "over_45": "Over 4.5 goles",
    "under_15": "Under 1.5 goles",
    "under_25": "Under 2.5 goles",
    "under_35": "Under 3.5 goles",
    "under_45": "Under 4.5 goles",
    "btts": "Ambos anotan",
}


def simulate_markets(
    lam_home: float,
    lam_away: float,
    n: int = 10000,
    rng: Optional[np.random.Generator] = None,
) -> Dict[Tuple[str, str], float]:
    """Empirical market probabilities from n simulated scorelines.

    Returns a dict keyed by (market, selection) → probability in [0, 1].
    """
    rng = rng or np.random.default_rng()
    lh = max(0.01, float(lam_home))
    la = max(0.01, float(lam_away))

    gh = rng.poisson(lh, n)
    ga = rng.poisson(la, n)
    total = gh + ga
    btts_yes = (gh > 0) & (ga > 0)

    def p(mask) -> float:
        return round(float(np.count_nonzero(mask)) / n, 5)

    return {
        ("1x2", "home"): p(gh > ga),
        ("1x2", "draw"): p(gh == ga),
        ("1x2", "away"): p(gh < ga),
        ("over_05", "over"): p(total > 0),
        ("over_15", "over"): p(total > 1),
        ("over_25", "over"): p(total > 2),
        ("over_35", "over"): p(total > 3),
        ("over_45", "over"): p(total > 4),
        ("under_15", "under"): p(total < 2),
        ("under_25", "under"): p(total < 3),
        ("under_35", "under"): p(total < 4),
        ("under_45", "under"): p(total < 5),
        ("btts", "yes"): p(btts_yes),
        ("btts", "no"): p(~btts_yes),
    }


def credible_interval(prob: float, n: int, z: float = 1.96) -> Tuple[float, float]:
    """95% credible interval for a Monte Carlo probability estimate.

    Normal approximation to the binomial proportion: with n simulations the
    sampling error is z*sqrt(p(1-p)/n). Wide interval ⇒ the estimate itself is
    uncertain (rare event or too few sims), narrow ⇒ trustworthy.
    """
    if n <= 0:
        return (prob, prob)
    se = (prob * (1.0 - prob) / n) ** 0.5
    return (round(max(0.0, prob - z * se), 5), round(min(1.0, prob + z * se), 5))


def kelly_fraction(prob: float, decimal_odds: float, cap: float = 0.10,
                   fraction: float = 0.25) -> float:
    """Fractional Kelly stake (share of bankroll) for a value bet.

    Full Kelly = (b*p - (1-p)) / b with b = decimal_odds - 1. We return a
    fraction of it (default quarter-Kelly) for safety and cap the result, so a
    single edge can't suggest betting the farm. Non-positive edge ⇒ 0 stake.
    """
    b = decimal_odds - 1.0
    if b <= 0:
        return 0.0
    full = (b * prob - (1.0 - prob)) / b
    if full <= 0:
        return 0.0
    return round(min(cap, full * fraction), 4)


def safety_score(model_prob: float, edge: float, confidence: float) -> float:
    """Composite ranking score (not a probability).

    Probability is the dominant term, scaled by model confidence; a positive
    value edge adds a bonus. Negative edges are ignored (floored at 0) so a
    badly-priced market never scores *below* its raw likelihood.
    """
    base = model_prob * (0.6 + 0.4 * max(0.0, min(1.0, confidence)))
    value_bonus = max(0.0, edge) * 0.5
    return round(base + value_bonus, 5)


def _pick_label(market: str, selection: str, home: str, away: str) -> str:
    if market == "1x2":
        return {"home": f"Gana {home}", "draw": "Empate", "away": f"Gana {away}"}[selection]
    if market == "btts":
        return "Ambos anotan" if selection == "yes" else "No ambos anotan"
    return MARKET_LABELS.get(market, market)


def _confidence_word(conf: float) -> str:
    return "alto" if conf >= 0.70 else ("medio" if conf >= 0.50 else "bajo")


def build_rationale(p: Dict) -> str:
    """Plain-Spanish justification of why a pick is a reasonable bet.

    Combines the model probability, the market-specific reason (favourite,
    goal expectancy, etc.), the value vs the real bookmaker odd, and how much
    the underlying models agree (confidence).
    """
    prob_pct = round(p["model_prob"] * 100)
    market, sel = p["market"], p["selection"]
    total = p.get("exp_goals_total")
    parts: List[str] = [f"El modelo le da {prob_pct}% de acierto (Monte Carlo, miles de simulaciones)."]

    if market == "1x2" and sel == "home":
        parts.append(f"{p['home_team']} llega como favorito por fuerza (ELO + forma reciente) y juega en casa.")
    elif market == "1x2" and sel == "away":
        parts.append(f"{p['away_team']} es superior según el modelo aun jugando fuera.")
    elif market == "1x2" and sel == "draw":
        parts.append("Equipos parejos: el empate concentra probabilidad.")
    elif market.startswith("over"):
        parts.append(f"Partido de perfil ofensivo: ~{total} goles esperados entre ambos.")
    elif market.startswith("under"):
        parts.append(f"Pocos goles proyectados (~{total} esperados): defensas o ataques flojos.")
    elif market == "btts" and sel == "yes":
        parts.append("Los dos ataques generan; ambos suelen anotar.")
    elif market == "btts" and sel == "no":
        parts.append("Al menos un equipo tiende a dejar su portería en cero.")

    if p["source"] == "market":
        imp = round(p["implied_prob"] * 100)
        if p["edge"] > 0:
            parts.append(
                f"{p['bookmaker']} paga {p['decimal_odds']} (probabilidad implícita {imp}%), "
                f"así que el modelo ve +{round(p['edge'] * 100)}% de valor."
            )
        else:
            parts.append(f"{p['bookmaker']} paga {p['decimal_odds']}; sin valor extra (precio justo o en contra).")
    else:
        parts.append(f"Sin odds de casa para este mercado; momio justo {p['decimal_odds']}.")

    conf = p.get("model_confidence", 0.0)
    parts.append(f"Acuerdo entre los modelos: {_confidence_word(conf)} ({conf:.2f}).")

    lo, hi = p.get("prob_ci_low"), p.get("prob_ci_high")
    if lo is not None and hi is not None:
        parts.append(f"Intervalo de confianza 95%: {round(lo * 100)}%–{round(hi * 100)}%.")
    kelly = p.get("kelly_fraction", 0.0)
    if kelly and kelly > 0:
        parts.append(f"Stake sugerido (Kelly fraccional): {round(kelly * 100, 1)}% del bankroll.")
    return " ".join(parts)


def simulated_match_picks(
    match: Match,
    odds_index: Optional[Dict] = None,
    n: int = 10000,
    rng: Optional[np.random.Generator] = None,
    apply_band: bool = True,
    min_prob: float = DEFAULT_MIN_PROB,
    max_prob: float = DEFAULT_MAX_PROB,
) -> List[Dict]:
    """Safe-bet picks for one match, ranked by safety score descending."""
    pred: Optional[Prediction] = match.prediction
    if pred is None:
        return []
    odds_index = odds_index or {}
    home = match.home_team.name
    away = match.away_team.name
    confidence = float(pred.model_confidence or 0.0)

    probs = simulate_markets(pred.lambda_home, pred.lambda_away, n=n, rng=rng)
    exp_home = round(float(pred.lambda_home), 2)
    exp_away = round(float(pred.lambda_away), 2)
    exp_total = round(exp_home + exp_away, 2)

    picks: List[Dict] = []
    for (market, selection), prob in probs.items():
        if apply_band and not (min_prob <= prob <= max_prob):
            continue
        real = odds_index.get((match.id, market, selection))
        if real is not None:
            decimal_odds = round(real.decimal_odds, 2)
            source = "market"
            bookmaker = real.bookmaker
        else:
            decimal_odds = _fair_odds(prob)
            source = "fair"
            bookmaker = None
        implied = round(1.0 / decimal_odds, 5) if decimal_odds > 0 else 0.0
        edge = round(prob - implied, 5)
        ci_low, ci_high = credible_interval(prob, n)
        pick = {
            "match_id": match.id,
            "home_team": home,
            "away_team": away,
            "kickoff_utc": match.kickoff_utc.isoformat(),
            "market": market,
            "selection": selection,
            "label": _pick_label(market, selection, home, away),
            "model_prob": prob,
            "prob_ci_low": ci_low,
            "prob_ci_high": ci_high,
            "decimal_odds": decimal_odds,
            "implied_prob": implied,
            "edge": edge,
            "kelly_fraction": kelly_fraction(prob, decimal_odds),
            "source": source,
            "bookmaker": bookmaker,
            "model_confidence": round(confidence, 4),
            "safety_score": safety_score(prob, edge, confidence),
            "exp_goals_home": exp_home,
            "exp_goals_away": exp_away,
            "exp_goals_total": exp_total,
        }
        pick["rationale"] = build_rationale(pick)
        picks.append(pick)
    picks.sort(key=lambda x: x["safety_score"], reverse=True)
    return picks


def safe_bets(
    db: Session,
    limit: int = 20,
    n: int = 10000,
    per_match: int = 1,
    min_prob: float = DEFAULT_MIN_PROB,
    max_prob: float = DEFAULT_MAX_PROB,
    max_per_market: Optional[int] = None,
    value_only: bool = False,
) -> List[Dict]:
    """Top safe picks across all upcoming matches, ranked by safety score.

    Takes the strongest `per_match` picks from each fixture so the board spans
    many games instead of repeating the same near-lock market everywhere, and
    caps how many picks share one market (`max_per_market`) so a single generic
    near-lock (e.g. Under 3.5) can't flood the whole board — keeping it varied
    and useful instead of 40 identical rows. Defaults to ~1/4 of `limit`.

    `value_only` keeps only picks priced against a real bookmaker odd where the
    model sees positive value (edge > 0).
    """
    if max_per_market is None:
        max_per_market = max(2, limit // 4)

    matches = (
        db.query(Match)
        .options(
            joinedload(Match.home_team),
            joinedload(Match.away_team),
            joinedload(Match.prediction),
        )
        .filter(Match.played == False)  # noqa: E712
        .all()
    )
    idx = _odds_index(db, [m.id for m in matches])
    rng = np.random.default_rng()

    # Pool ALL in-band, non-trivial picks across matches so the diversifier has
    # the full spread of markets to choose from. Capping happens afterwards.
    all_picks: List[Dict] = []
    for m in matches:
        picks = simulated_match_picks(
            m, idx, n=n, rng=rng, min_prob=min_prob, max_prob=max_prob
        )
        for p in picks:
            if p["market"] in TRIVIAL_MARKETS:
                continue
            if value_only and not (p["source"] == "market" and p["edge"] > 0):
                continue
            all_picks.append(p)

    all_picks.sort(key=lambda x: x["safety_score"], reverse=True)
    return diversify_by_market(
        all_picks, limit=limit,
        max_per_market=max_per_market, max_per_match=per_match,
    )


def best_bet_per_match(
    db: Session,
    n: int = 8000,
    upcoming_only: bool = True,
) -> List[Dict]:
    """One best pick for every match, returned in chronological order.

    Each match contributes its single strongest selection (by safety score),
    so the caller gets a date-ordered fixture list where every game carries its
    own data-backed recommendation — not a cross-match leaderboard. The band is
    relaxed (every fixture yields a pick) but trivial near-locks are still
    skipped so the suggestion is informative.
    """
    q = (
        db.query(Match)
        .options(
            joinedload(Match.home_team),
            joinedload(Match.away_team),
            joinedload(Match.prediction),
        )
    )
    if upcoming_only:
        q = q.filter(Match.played == False)  # noqa: E712
    matches = q.order_by(Match.kickoff_utc.asc()).all()

    idx = _odds_index(db, [m.id for m in matches])
    rng = np.random.default_rng()

    out: List[Dict] = []
    for m in matches:
        picks = simulated_match_picks(m, idx, n=n, rng=rng, apply_band=False)
        picks = [p for p in picks if p["market"] not in TRIVIAL_MARKETS]
        if not picks:
            continue
        best = picks[0]
        out.append({
            "match_id": m.id,
            "home_team": m.home_team.name,
            "away_team": m.away_team.name,
            "kickoff_utc": m.kickoff_utc.isoformat(),
            "stage": m.stage,
            "group": m.group,
            "best_pick": best,
        })
    return out


def diversify_by_market(
    picks: List[Dict],
    limit: int,
    max_per_market: int,
    max_per_match: int = 2,
) -> List[Dict]:
    """Cap picks per market and per match so the board stays varied.

    `picks` must be pre-sorted (best first). Keeps at most `max_per_market` of
    any one market and `max_per_match` from any one fixture; if that leaves the
    board short of `limit`, backfills with the best of the overflow so the
    caller always gets up to `limit` picks when enough exist.
    """
    selected: List[Dict] = []
    overflow: List[Dict] = []
    per_market: Dict[str, int] = {}
    per_match: Dict[int, int] = {}
    for p in picks:
        mk = p["market"]
        mid = p["match_id"]
        if (per_market.get(mk, 0) < max_per_market
                and per_match.get(mid, 0) < max_per_match):
            per_market[mk] = per_market.get(mk, 0) + 1
            per_match[mid] = per_match.get(mid, 0) + 1
            selected.append(p)
        else:
            overflow.append(p)
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        selected.extend(overflow[: limit - len(selected)])
    # Caps bounded the *count* per market/match; present the chosen set best-first.
    selected.sort(key=lambda x: x["safety_score"], reverse=True)
    return selected[:limit]


def build_parlay(picks: List[Dict], legs: int = 3) -> Dict:
    """Assemble an accumulator from the safest independent single-match picks.

    Picks must already be sorted by safety (descending). One leg per distinct
    match keeps legs approximately independent so the joint probability is the
    product of the legs. Returns combined probability, combined decimal odds,
    fair odds and expected value (per unit stake).
    """
    chosen: List[Dict] = []
    seen_matches = set()
    for p in picks:
        mid = p["match_id"]
        if mid in seen_matches:
            continue
        seen_matches.add(mid)
        chosen.append(p)
        if len(chosen) >= legs:
            break

    if not chosen:
        return {
            "legs": [],
            "combined_prob": 0.0,
            "combined_odds": 0.0,
            "fair_odds": 0.0,
            "expected_value": 0.0,
        }

    combined_prob = 1.0
    combined_odds = 1.0
    for p in chosen:
        combined_prob *= p["model_prob"]
        combined_odds *= p["decimal_odds"]

    fair_odds = round(1.0 / combined_prob, 2) if combined_prob > 0 else 0.0
    expected_value = round(combined_prob * combined_odds - 1.0, 4)

    return {
        "legs": chosen,
        "combined_prob": round(combined_prob, 5),
        "combined_odds": round(combined_odds, 2),
        "fair_odds": fair_odds,
        "expected_value": expected_value,
    }


# Tournament outright markets → which simulate_tournament field backs each.
OUTRIGHT_MARKETS = {
    "champion": "champion",
    "final": "reach_final",
    "semifinal": "reach_sf",
    "round_of_16": "reach_r16",
}


def _bracket_feasible(db: Session) -> bool:
    """The tournament simulator hard-codes a 32-team knockout (12 groups of ~4).
    Guard against partial data so the endpoint degrades gracefully instead of
    raising an IndexError mid-simulation."""
    from collections import Counter
    from app.models.match import Match

    rows = db.query(Match.group).filter(Match.group.isnot(None)).all()
    counts = Counter(g for (g,) in rows if g)  # teams aren't unique here, but
    # every group with a full round-robin appears in >= 3 matches; require the
    # canonical 12 groups before attempting the bracket.
    return len(counts) >= 12


def outright_bets(db: Session, n: int = 3000, top: int = 10) -> Dict:
    """Tournament outright picks (champion / reach a stage) from a full-bracket
    Monte Carlo, expressed as bets with fair odds = 1 / probability."""
    if not _bracket_feasible(db):
        return {"n": 0, "markets": {m: [] for m in OUTRIGHT_MARKETS}}
    sim = simulate_tournament(db, n=n)
    teams = sim["teams"]
    markets: Dict[str, List[Dict]] = {}
    for market, field in OUTRIGHT_MARKETS.items():
        ranked = sorted(teams, key=lambda t: t.get(field, 0.0), reverse=True)
        rows = []
        for t in ranked[:top]:
            prob = t.get(field, 0.0)
            if prob <= 0:
                continue
            rows.append({
                "team": t["team"],
                "elo": t["elo"],
                "prob": prob,
                "fair_odds": round(1.0 / prob, 2),
            })
        markets[market] = rows
    return {"n": sim["n"], "markets": markets}
