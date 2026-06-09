#!/bin/bash
set -e
source .venv/bin/activate

# Populate DB on startup
python -m pipeline.run

# Start API in background
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Start daily scheduler (blocking)
python scheduler.py
