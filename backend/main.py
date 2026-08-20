import asyncio
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

from backend.assets import load_assets
from backend.db import add_subscriber, init_db
from backend.geocode import geocode_address
from backend.hazards import fetch_all_hazards
from backend.llm import generate_briefing
from backend.notify import start_poller
from backend.risk import score_assets

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Grid Guardian", description="Real-time critical infrastructure risk monitor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    address: str
    criticality: str = "high"


@app.on_event("startup")
async def on_startup():
    init_db()
    asyncio.create_task(start_poller())


@app.post("/api/register")
async def register(req: RegisterRequest):
    coords = await geocode_address(req.address)
    if coords is None:
        raise HTTPException(status_code=400, detail="Could not geocode that address")
    lat, lon = coords
    subscriber_id = add_subscriber(req.name, req.email, req.address, lat, lon, req.criticality)
    return {"id": subscriber_id, "lat": lat, "lon": lon, "message": "Registered. You'll be emailed if a hazard is detected near this location."}


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
