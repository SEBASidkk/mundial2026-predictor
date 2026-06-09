"""
Daily pipeline scheduler. Run with: python scheduler.py
Triggers at 02:00 UTC.
"""
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from pipeline.run import run

logging.basicConfig(level=logging.INFO)

scheduler = BlockingScheduler(timezone="UTC")
scheduler.add_job(run, "cron", hour=2, minute=0, id="daily_pipeline")

if __name__ == "__main__":
    logging.info("Scheduler started. Daily pipeline at 02:00 UTC.")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()
