import asyncio
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

from backend.auth import require_org
from backend.db import (
    add_asset,
    add_subscriber,
    create_organization,
    init_db,
    list_assets,
    list_incidents,
)
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


class OrgRegisterRequest(BaseModel):
    name: str
    email: EmailStr


class AssetRequest(BaseModel):
    name: str
    type: str
    address: str
    criticality: str = "high"


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    address: str
    criticality: str = "high"


@app.on_event("startup")
async def on_startup():
    init_db()
    asyncio.create_task(start_poller())


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/orgs/register")
async def register_org(req: OrgRegisterRequest):
    org = create_organization(req.name, req.email)
    return {
        "org_id": org["id"],
        "token": org["token"],
        "message": "Save this token — it's required as the X-Org-Token header on every API call for your organization.",
    }


@app.post("/api/register")
async def register(req: RegisterRequest, org: dict = Depends(require_org)):
    coords = await geocode_address(req.address)
    if coords is None:
        raise HTTPException(status_code=400, detail="Could not geocode that address")
    lat, lon = coords
    subscriber_id = add_subscriber(org["id"], req.name, req.email, req.address, lat, lon, req.criticality, req.phone)
    return {
        "id": subscriber_id,
        "lat": lat,
        "lon": lon,
        "message": "Registered. You'll be emailed (and texted, if a phone number was given) if a hazard is detected near this location.",
    }


@app.get("/api/assets")
async def get_assets(org: dict = Depends(require_org)):
    return list_assets(org["id"])


@app.post("/api/assets")
async def create_asset(req: AssetRequest, org: dict = Depends(require_org)):
    coords = await geocode_address(req.address)
    if coords is None:
        raise HTTPException(status_code=400, detail="Could not geocode that address")
    lat, lon = coords
    asset_id = add_asset(org["id"], req.name, req.type, lat, lon, req.criticality)
    return {"id": asset_id, "lat": lat, "lon": lon}


@app.get("/api/risk-assessment")
async def get_risk_assessment(org: dict = Depends(require_org)):
    assets = list_assets(org["id"])
    hazards = await fetch_all_hazards()
    scored = score_assets(assets, hazards)
    return {"hazard_count": len(hazards), "assets": scored}


@app.get("/api/briefing")
async def get_briefing(org: dict = Depends(require_org)):
    assets = list_assets(org["id"])
    hazards = await fetch_all_hazards()
    scored = score_assets(assets, hazards)
    briefing = generate_briefing(scored)
    return {"briefing": briefing, "hazard_count": len(hazards)}


@app.get("/api/incidents")
async def get_incidents(org: dict = Depends(require_org)):
    return list_incidents(org["id"])


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")
