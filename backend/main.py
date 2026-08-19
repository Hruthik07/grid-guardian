from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.assets import load_assets
from backend.hazards import fetch_all_hazards
from backend.llm import generate_briefing
from backend.risk import score_assets

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Grid Guardian", description="Real-time critical infrastructure risk monitor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/assets")
async def get_assets():
    return load_assets()


@app.get("/api/risk-assessment")
async def get_risk_assessment():
    assets = load_assets()
    hazards = await fetch_all_hazards()
    scored = score_assets(assets, hazards)
    return {"hazard_count": len(hazards), "assets": scored}


@app.get("/api/briefing")
async def get_briefing():
    assets = load_assets()
    hazards = await fetch_all_hazards()
    scored = score_assets(assets, hazards)
    briefing = generate_briefing(scored)
    return {"briefing": briefing, "hazard_count": len(hazards)}


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")
