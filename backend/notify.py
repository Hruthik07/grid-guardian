import asyncio
import hashlib
import logging
import os

import httpx

from backend.assets import CRITICALITY_WEIGHT
from backend.db import has_been_notified, list_subscribers, mark_notified
from backend.hazards import fetch_all_hazards
from backend.risk import score_assets

logger = logging.getLogger("grid_guardian.notify")

RESEND_URL = "https://api.resend.com/emails"
POLL_INTERVAL_SECONDS = 5 * 60
FROM_ADDRESS = "Grid Guardian <alerts@resend.dev>"


def _hazard_key(hazard: dict) -> str:
    raw = f"{hazard['source']}|{hazard['event_type']}|{hazard['headline']}|{hazard.get('effective', '')}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _subscribers_as_assets(subscribers: list[dict]) -> list[dict]:
    assets = []
    for s in subscribers:
        assets.append({
            "asset_id": f"sub-{s['id']}",
            "name": s["name"],
            "type": "registered_location",
            "lat": s["lat"],
            "lon": s["lon"],
            "criticality": s["criticality"],
            "criticality_weight": CRITICALITY_WEIGHT.get(s["criticality"], 0.5),
        })
    return assets


async def _send_email(client: httpx.AsyncClient, to_email: str, subject: str, body: str) -> None:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        logger.warning("RESEND_API_KEY not set; skipping email to %s: %s", to_email, subject)
        return
    try:
        resp = await client.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"from": FROM_ADDRESS, "to": [to_email], "subject": subject, "text": body},
            timeout=15,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)


async def check_and_notify_once() -> int:
    subscribers = list_subscribers()
    if not subscribers:
        return 0
    hazards = await fetch_all_hazards()
    assets = _subscribers_as_assets(subscribers)
    scored = score_assets(assets, hazards)
    scored_by_id = {a["asset_id"]: a for a in scored}

    sent = 0
    async with httpx.AsyncClient() as client:
        for s in subscribers:
            scored_asset = scored_by_id.get(f"sub-{s['id']}")
            if not scored_asset or scored_asset["risk_score"] <= 0:
                continue
            for hazard_hit in scored_asset["hazards"]:
                key = f"{hazard_hit['source']}|{hazard_hit['event_type']}|{hazard_hit['headline']}"
                key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
                if has_been_notified(s["id"], key_hash):
                    continue
                subject = f"Grid Guardian Alert: {hazard_hit['event_type']} near {s['address']}"
                body = (
                    f"Hi {s['name']},\n\n"
                    f"A {hazard_hit['event_type']} ({hazard_hit['severity']}) has been detected near your "
                    f"registered location ({s['address']}).\n\n"
                    f"Details: {hazard_hit['headline']}\n"
                    f"Source: {hazard_hit['source']}\n\n"
                    "— Grid Guardian"
                )
                await _send_email(client, s["email"], subject, body)
                mark_notified(s["id"], key_hash)
                sent += 1
    return sent


async def start_poller() -> None:
    while True:
        try:
            sent = await check_and_notify_once()
            if sent:
                logger.info("Sent %d hazard alert email(s)", sent)
        except Exception:
            logger.exception("Error during hazard poll cycle")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
