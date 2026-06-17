"""Adaptive pipeline scheduler — keeps results, predictions and odds fresh.

Run with: python scheduler.py

Instead of a fixed cadence, the refresh interval scales with how close the next
kickoff is, so odds and predictions are tight when it matters and we don't burn
The Odds API quota overnight:

  * a match kicking off within LIVE_WINDOW  → refresh every LIVE_MINUTES
  * next match within SOON_WINDOW           → refresh every SOON_MINUTES
  * otherwise (quiet period)                → refresh every IDLE_HOURS

Each tick reschedules itself based on the fixture list, and one refresh runs
immediately on startup. Override any threshold via env vars.
"""
import logging
import os
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models.match import Match
from pipeline.run import run

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

LIVE_WINDOW = timedelta(hours=float(os.environ.get("LIVE_WINDOW_HOURS", "2")))
SOON_WINDOW = timedelta(hours=float(os.environ.get("SOON_WINDOW_HOURS", "12")))
LIVE_MINUTES = max(1, int(os.environ.get("LIVE_MINUTES", "5")))
SOON_MINUTES = max(5, int(os.environ.get("SOON_MINUTES", "30")))
IDLE_HOURS = max(1, int(os.environ.get("IDLE_HOURS", "6")))

scheduler = BackgroundScheduler(timezone="UTC")


def _seconds_until_next_kickoff() -> float | None:
    """Seconds to the soonest upcoming (or in-progress) kickoff, or None."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        # Include matches that may still be in play (kickoff within ~3h).
        rows = (
            db.query(Match.kickoff_utc)
            .filter(Match.played == False)  # noqa: E712
            .order_by(Match.kickoff_utc.asc())
            .all()
        )
        for (ko,) in rows:
            if ko is None:
                continue
            if ko.tzinfo is None:
                ko = ko.replace(tzinfo=timezone.utc)
            delta = (ko - now).total_seconds()
            if delta >= -3 * 3600:  # not yet finished
                return delta
        return None
    finally:
        db.close()


def _next_interval_seconds() -> int:
    secs = _seconds_until_next_kickoff()
    if secs is None:
        return IDLE_HOURS * 3600
    gap = timedelta(seconds=max(0, secs))
    if gap <= LIVE_WINDOW:
        return LIVE_MINUTES * 60
    if gap <= SOON_WINDOW:
        return SOON_MINUTES * 60
    return IDLE_HOURS * 3600


def tick():
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        log.exception("Pipeline refresh failed: %s", exc)
    interval = _next_interval_seconds()
    log.info("Next refresh in %d min.", interval // 60)
    scheduler.add_job(
        tick, "date",
        run_date=datetime.now(timezone.utc) + timedelta(seconds=interval),
        id="pipeline_refresh", replace_existing=True,
    )


if __name__ == "__main__":
    log.info("Running initial pipeline refresh on startup...")
    scheduler.start()
    tick()  # runs now and schedules the next adaptive tick
    try:
        import time
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        scheduler.shutdown()
