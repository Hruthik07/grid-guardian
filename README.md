# Grid Guardian

Real-time critical infrastructure risk monitor. Live public hazard feeds (NOAA,
USGS, NASA EONET) are cross-referenced geospatially against a customer's asset
portfolio, scored, and summarized by an open-source LLM into an operator-facing
briefing — with proactive email alerting and a persistent incident audit log.

**Live demo:** https://grid-guardian-7djv.onrender.com
*(free-tier hosting — the first request after ~15 min idle can take up to 50s to wake up)*

## The problem

Organizations responsible for multiple physical sites — hospital networks, utility
companies, logistics operators — have no single tool that answers "given what's
actually happening in the world right now, which of my facilities are at risk, and
what should I do first?" Today that means manually checking NOAA, USGS, and news
feeds and cross-referencing by hand. Grid Guardian automates that loop end to end,
using only real government data — nothing in the risk pipeline is mocked or simulated.

## How it works

1. **Live hazard ingestion** — concurrently fetches NOAA active weather alerts,
   USGS real-time earthquakes, and NASA EONET wildfire/storm events, normalizing
   all three into one shape.
2. **Geospatial risk scoring** — point-in-polygon tests for NOAA warning zones,
   haversine-distance decay for point hazards (quakes, wildfires), weighted by
   each asset's criticality tier.
3. **LLM ops briefing** — the top at-risk assets are summarized by an open-source
   model (`openai/gpt-oss-120b`, hosted free on Groq) into a prioritized,
   actionable briefing for a shift supervisor.
4. **Multi-tenant accounts** — each organization gets a private, isolated asset
   portfolio and subscriber list behind an opaque bearer token (`X-Org-Token`).
5. **Proactive alerting** — a background poller re-scores every org's portfolio
   every 5 minutes and emails (via Resend) any subscriber whose registered
   location now intersects a new hazard, deduplicated per hazard occurrence.
6. **Incident audit log** — every new hazard-to-asset match is persisted with a
   detection timestamp and notified flag, so risk history is reviewable, not
   just live.

## Architecture

```
backend/
  hazards.py   live NOAA / USGS / EONET fetchers, normalized to one hazard shape
  geo.py       haversine distance, point-in-polygon
  risk.py      severity x criticality x proximity scoring engine
  db.py        SQLite: organizations, assets, subscribers, incidents
  auth.py      X-Org-Token bearer auth, scopes every request to one org
  geocode.py   free Nominatim (OpenStreetMap) address -> lat/lon
  llm.py       Groq-hosted open-source LLM briefing generation
  notify.py    background poller: re-scores all orgs, emails new hazards
  sms.py       Twilio SMS (wired, inactive until Twilio creds are set)
  main.py      FastAPI app, all endpoints
frontend/
  index.html   org sign-in/registration gate, live map, risk table,
               incident log, asset + subscriber registration forms
data/
  assets.csv   seed data for the shared read-only demo org
render.yaml    Render Blueprint for one-click deployment
```

## Running locally

```bash
python -m venv .venv
./.venv/Scripts/activate       # Windows; source .venv/bin/activate on Unix
pip install -r requirements.txt
cp .env.example .env           # fill in GROQ_API_KEY and RESEND_API_KEY (both free)
uvicorn backend.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000`. Click "View the shared demo portfolio" for the
pre-loaded 20-asset demo, or register your own organization for a private,
writable portfolio.

- **`GROQ_API_KEY`** — free at [console.groq.com](https://console.groq.com);
  without it, briefings fall back to a plain-text summary instead of failing.
- **`RESEND_API_KEY`** — free at [resend.com](https://resend.com) (3,000
  emails/month); without it, alert emails are skipped (logged, not sent).

## Deploying

`render.yaml` is a ready-to-use [Render](https://render.com) Blueprint: New +
→ Blueprint → connect this repo → fill in `GROQ_API_KEY`/`RESEND_API_KEY` →
Apply. Render's free web service tier is used — see Known Limitations below.

## Known limitations (honest, not hidden)

- **Ephemeral storage.** Render's free tier does not guarantee filesystem
  persistence across restarts/redeploys. The live risk-scoring engine is
  unaffected (it always pulls fresh hazard data), but registered orgs and
  subscribers on the free deployment aren't guaranteed to survive indefinitely.
  A production deployment would use a managed Postgres instance instead of
  local SQLite.
- **SMS is wired but inactive.** `backend/sms.py` and the subscriber phone
  field exist and will activate automatically once Twilio credentials are set,
  but weren't enabled for this deployment: Twilio trial accounts can only text
  pre-verified numbers, not real public users, so it wouldn't add real value
  yet without a paid Twilio account.
- **Wildfire/quake proximity radii are estimates, not precise perimeters.**
  Point hazards use a severity-scaled influence radius around a single
  coordinate rather than actual fire-perimeter or shake-intensity data. This
  is flagged here deliberately rather than presented as more precise than it is.
- **The shared demo org is read-only** by design (its token is publicly
  visible in the frontend JS) — write endpoints reject it with a 403. Register
  your own organization for a private, writable portfolio.

## Stage-by-stage build log

See [STAGES.md](STAGES.md) for the full incremental build history, what was
verified at each stage, and the reasoning behind scope decisions (e.g. why SMS
was scoped out for now).
