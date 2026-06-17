"""Manual pipeline refresh.

The pipeline normally runs on the adaptive scheduler, but the data can look
stale (e.g. yesterday's fixtures still showing) if the scheduler isn't running
or a result just landed. This lets the UI trigger a full refresh on demand —
pull latest fixtures/results/odds, re-learn weights and regenerate predictions.

The run is heavy (network I/O) so it executes in a background thread and the
endpoint returns immediately. A module-level lock prevents overlapping runs;
the UI polls `GET /api/refresh/status` to know when it has finished.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter

from pipeline.run import run

log = logging.getLogger(__name__)
router = APIRouter()

_lock = threading.Lock()
_state = {
    "running": False,
    "last_run": None,        # ISO timestamp of last completed run
    "last_error": None,      # str of last failure, if any
    "started_at": None,      # ISO timestamp of the in-flight run
}


def _run_pipeline() -> None:
    try:
        run()
        _state["last_run"] = datetime.now(timezone.utc).isoformat()
        _state["last_error"] = None
    except Exception as exc:  # noqa: BLE001
        log.exception("Manual refresh failed: %s", exc)
        _state["last_error"] = str(exc)
    finally:
        _state["running"] = False
        _lock.release()


@router.post("/refresh")
def trigger_refresh():
    """Start a pipeline refresh in the background (no-op if one is running)."""
    if not _lock.acquire(blocking=False):
        return {"status": "already_running", **_public_state()}
    _state["running"] = True
    _state["started_at"] = datetime.now(timezone.utc).isoformat()
    threading.Thread(target=_run_pipeline, daemon=True).start()
    return {"status": "started", **_public_state()}


@router.get("/refresh/status")
def refresh_status():
    return _public_state()


def _public_state() -> dict:
    return {
        "running": _state["running"],
        "last_run": _state["last_run"],
        "last_error": _state["last_error"],
        "started_at": _state["started_at"],
    }
