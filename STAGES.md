# Grid Guardian — Implementation Stages

Real-time critical infrastructure risk monitor. Live public hazard feeds (NOAA,
USGS, NASA EONET) cross-referenced against a customer asset registry, scored
geospatially, and summarized by an LLM into an operator-facing briefing.

Each stage below is committed and pushed to GitHub individually.

- [x] **Stage 1 — Data layer**: sample asset registry (`data/assets.csv`), `requirements.txt`
- [x] **Stage 2 — Hazard ingestion**: NOAA/USGS/EONET fetchers + geo utilities (`backend/hazards.py`, `backend/geo.py`)
- [x] **Stage 3 — Risk scoring engine**: proximity + severity + criticality scoring (`backend/risk.py`, `backend/assets.py`)
- [x] **Stage 4 — LLM briefing**: Groq-hosted open-source model generates operator briefings (`backend/llm.py`)
- [x] **Stage 5 — API layer**: FastAPI app wiring endpoints together (`backend/main.py`)
- [x] **Stage 6 — Frontend dashboard**: Leaflet map + risk table + briefing panel (`frontend/index.html`)
- [x] **Stage 7 — Local end-to-end test**: verified live NOAA/USGS/EONET data flows through risk scoring into the dashboard (real wildfire/earthquake data confirmed in screenshot)
- [x] **Stage 7.5 — Registration + proactive alerting**: signup form geocodes an address into a monitored subscriber (`backend/db.py`, `backend/geocode.py`), background poller (`backend/notify.py`) checks live hazards every 5 min and emails subscribers via Resend when a hazard intersects their location, deduped per hazard occurrence. Verified live: registered a real address, confirmed real email delivery via Resend.
- [ ] **Stage 8 — Deployment**: push to GitHub, deploy on Render free tier, get public URL
- [ ] **Stage 9 — Documentation**: final README with architecture, setup, and demo instructions
