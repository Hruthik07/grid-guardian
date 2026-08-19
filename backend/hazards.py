"""Fetchers for free, no-key public hazard feeds: NOAA weather alerts,
USGS earthquakes, and NASA EONET natural events. Each returns a list of
normalized Hazard dicts."""

import asyncio

import httpx

NOAA_ALERTS_URL = "https://api.weather.gov/alerts/active?status=actual&message_type=alert"
USGS_QUAKES_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
EONET_EVENTS_URL = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=50"

HEADERS = {"User-Agent": "GridGuardianPrototype (portfolio demo; contact: g.d.hruthik2001@gmail.com)"}

SEVERITY_SCORE = {
    "extreme": 1.0,
    "severe": 0.8,
    "moderate": 0.5,
    "minor": 0.25,
    "unknown": 0.15,
}


async def fetch_noaa_alerts(client: httpx.AsyncClient) -> list[dict]:
    hazards = []
    try:
        r = await client.get(NOAA_ALERTS_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        for f in r.json().get("features", []):
            props = f.get("properties", {})
            geom = f.get("geometry")
            if not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
                continue
            polygons = geom["coordinates"] if geom["type"] == "Polygon" else [p[0] for p in geom["coordinates"]]
            sev = (props.get("severity") or "unknown").lower()
            hazards.append({
                "source": "NOAA",
                "event_type": props.get("event", "Weather Alert"),
                "severity": sev,
                "severity_score": SEVERITY_SCORE.get(sev, 0.15),
                "headline": props.get("headline", ""),
                "geometry_type": "polygon",
                "polygons": polygons if geom["type"] == "Polygon" else geom["coordinates"],
                "effective": props.get("effective"),
                "expires": props.get("expires"),
            })
    except (httpx.HTTPError, ValueError):
        pass
    return hazards


async def fetch_usgs_quakes(client: httpx.AsyncClient) -> list[dict]:
    hazards = []
    try:
        r = await client.get(USGS_QUAKES_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        for f in r.json().get("features", []):
            props = f.get("properties", {})
            coords = f.get("geometry", {}).get("coordinates")
            if not coords:
                continue
            mag = props.get("mag") or 0
            sev = "extreme" if mag >= 6 else "severe" if mag >= 5 else "moderate" if mag >= 4 else "minor"
            hazards.append({
                "source": "USGS",
                "event_type": f"Earthquake M{mag}",
                "severity": sev,
                "severity_score": SEVERITY_SCORE.get(sev, 0.15),
                "headline": props.get("place", "Earthquake"),
                "geometry_type": "point",
                "lat": coords[1],
                "lon": coords[0],
                "effective": props.get("time"),
            })
    except (httpx.HTTPError, ValueError):
        pass
    return hazards


async def fetch_eonet_events(client: httpx.AsyncClient) -> list[dict]:
    hazards = []
    try:
        r = await client.get(EONET_EVENTS_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        for ev in r.json().get("events", []):
            geoms = ev.get("geometry", [])
            if not geoms:
                continue
            latest = geoms[-1]
            coords = latest.get("coordinates")
            if not coords or latest.get("type") != "Point":
                continue
            category = (ev.get("categories") or [{}])[0].get("title", "Natural Event")
            hazards.append({
                "source": "NASA EONET",
                "event_type": category,
                "severity": "severe",
                "severity_score": SEVERITY_SCORE["severe"],
                "headline": ev.get("title", category),
                "geometry_type": "point",
                "lat": coords[1],
                "lon": coords[0],
                "effective": latest.get("date"),
            })
    except (httpx.HTTPError, ValueError):
        pass
    return hazards


async def fetch_all_hazards() -> list[dict]:
    async with httpx.AsyncClient() as client:
        noaa, usgs, eonet = await asyncio.gather(
            fetch_noaa_alerts(client), fetch_usgs_quakes(client), fetch_eonet_events(client)
        )
    return noaa + usgs + eonet
