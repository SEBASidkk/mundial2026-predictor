"""API tests for the manual pipeline refresh endpoint (run patched out)."""
import time

from fastapi.testclient import TestClient

from app.main import app
import app.routers.refresh as refresh

client = TestClient(app)


def _wait_idle(timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not client.get("/api/refresh/status").json()["running"]:
            return
        time.sleep(0.02)


def test_refresh_runs_in_background(monkeypatch):
    calls = {"n": 0}

    def fake_run():
        calls["n"] += 1

    monkeypatch.setattr(refresh, "run", fake_run)

    r = client.post("/api/refresh")
    assert r.status_code == 200
    assert r.json()["status"] in ("started", "already_running")

    _wait_idle()
    status = client.get("/api/refresh/status").json()
    assert status["running"] is False
    assert status["last_run"] is not None
    assert status["last_error"] is None
    assert calls["n"] >= 1


def test_refresh_reports_errors(monkeypatch):
    def boom():
        raise RuntimeError("ingestion down")

    monkeypatch.setattr(refresh, "run", boom)
    client.post("/api/refresh")
    _wait_idle()
    status = client.get("/api/refresh/status").json()
    assert status["running"] is False
    assert "ingestion down" in (status["last_error"] or "")
