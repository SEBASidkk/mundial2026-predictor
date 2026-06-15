"""
Pipeline scheduler — keeps results, predictions and odds fresh during the
tournament. Run with: python scheduler.py

Refreshes every REFRESH_HOURS (default 3) so finished matches are ingested and
predictions for upcoming games are regenerated within a few hours of kickoff,
instead of waiting a full day. Also runs once immediately on startup.

Override the cadence with the REFRESH_HOURS env var.
"""
import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler

from pipeline.run import run

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

REFRESH_HOURS = max(1, int(os.environ.get("REFRESH_HOURS", "3")))

scheduler = BlockingScheduler(timezone="UTC")
scheduler.add_job(
    run, "interval", hours=REFRESH_HOURS, id="pipeline_refresh",
    next_run_time=None,  # set below so we can also fire once on startup
)


if __name__ == "__main__":
    log.info("Running initial pipeline refresh on startup...")
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        log.exception("Initial pipeline run failed: %s", exc)
    log.info("Scheduler started. Refreshing every %d hour(s).", REFRESH_HOURS)
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()
