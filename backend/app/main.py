from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app import models  # noqa: F401  (register all tables before create_all)
from app.routers import matches, teams, standings, model_meta, bets, tournament, refresh

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mundial 2026 Predictor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(matches.router, prefix="/api")
app.include_router(teams.router, prefix="/api")
app.include_router(standings.router, prefix="/api")
app.include_router(model_meta.router, prefix="/api")
app.include_router(bets.router, prefix="/api")
app.include_router(tournament.router, prefix="/api")
app.include_router(refresh.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
