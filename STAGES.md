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
- [x] **Stage 8 — Multi-tenant customer accounts**: organizations table with opaque bearer tokens (`X-Org-Token`), private per-org asset portfolios and subscriber lists, org self-registration + sign-in flow in the frontend (`backend/db.py`, `backend/auth.py`, `backend/main.py`). Verified: new org starts with an empty portfolio, fully isolated from the demo org's 20 assets.
- [x] **Stage 9 — Incident audit log**: every new hazard-to-asset/subscriber match is persisted (deduped) with a detection timestamp, notified flag, and full hazard context (`backend/db.py: log_incident`, `backend/notify.py`). Exposed via `/api/incidents` and rendered as a timeline in the dashboard. Verified: populated automatically by the background poller with real live wildfire/earthquake incidents.
- [~] **Stage 10 — SMS alerts**: scoped out for now. `backend/sms.py` and the subscriber phone field are in place and will activate automatically once `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN`/`TWILIO_FROM_NUMBER` are set — skipped because Twilio trial accounts can only SMS pre-verified numbers, not real public users, so it wouldn't add real value yet. Email (Resend) covers alerting for now.
- [ ] **Stage 11 — Deployment**: push to GitHub, deploy on Render free tier, get public URL
- [ ] **Stage 12 — Documentation**: final README with architecture, setup, and demo instructions
