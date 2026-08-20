import asyncio
import hashlib
import logging
import os

import httpx

from backend.db import (
    has_been_notified,
    list_assets,
    list_organizations,
    list_subscribers,
    log_incident,
    mark_notified,
)
from backend.hazards import fetch_all_hazards
from backend.risk import score_assets
from backend.sms import send_sms

logger = logging.getLogger("grid_guardian.notify")

RESEND_URL = "https://api.resend.com/emails"
POLL_INTERVAL_SECONDS = 5 * 60
FROM_ADDRESS = "Grid Guardian <alerts@resend.dev>"


def _subscribers_as_assets(subscribers: list[dict]) -> list[dict]:
    from backend.db import CRITICALITY_WEIGHT

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


async def _process_org(client: httpx.AsyncClient, org: dict, hazards: list[dict]) -> int:
    org_id = org["id"]
    assets = list_assets(org_id)
    subscribers = list_subscribers(org_id)
    subscriber_assets = _subscribers_as_assets(subscribers)
    subscribers_by_asset_id = {f"sub-{s['id']}": s for s in subscribers}

    scored = score_assets(assets + subscriber_assets, hazards)
    sent = 0

    for scored_asset in scored:
        if scored_asset["risk_score"] <= 0:
            continue
        is_subscriber = scored_asset["asset_id"].startswith("sub-")
        target_type = "subscriber" if is_subscriber else "asset"
        target_id = int(scored_asset["asset_id"].split("-")[1])

        for hit in scored_asset["hazards"]:
            is_new = log_incident(
                org_id, target_type, target_id, scored_asset["name"], hit,
                scored_asset["risk_score"], hit["contribution"], notified=is_subscriber,
            )
            if not is_new or not is_subscriber:
                continue

            subscriber = subscribers_by_asset_id[scored_asset["asset_id"]]
            hazard_key = hashlib.sha256(
                f"{hit['source']}|{hit['event_type']}|{hit['headline']}".encode()
            ).hexdigest()[:16]
            if has_been_notified(subscriber["id"], hazard_key):
                continue

            subject = f"Grid Guardian Alert: {hit['event_type']} near {subscriber['address']}"
            body = (
                f"Hi {subscriber['name']},\n\n"
                f"A {hit['event_type']} ({hit['severity']}) has been detected near your registered "
                f"location ({subscriber['address']}).\n\nDetails: {hit['headline']}\nSource: {hit['source']}"
                "\n\n— Grid Guardian"
            )
            await _send_email(client, subscriber["email"], subject, body)
            if subscriber.get("phone"):
                send_sms(subscriber["phone"], f"Grid Guardian: {hit['event_type']} ({hit['severity']}) near {subscriber['address']}. {hit['headline']}")
            mark_notified(subscriber["id"], hazard_key)
            sent += 1

    return sent


async def check_and_notify_once() -> int:
    orgs = list_organizations()
    if not orgs:
        return 0
    hazards = await fetch_all_hazards()
    total_sent = 0
    async with httpx.AsyncClient() as client:
        for org in orgs:
            total_sent += await _process_org(client, org, hazards)
    return total_sent


async def start_poller() -> None:
    while True:
        try:
            sent = await check_and_notify_once()
            if sent:
                logger.info("Sent %d hazard alert notification(s)", sent)
        except Exception:
            logger.exception("Error during hazard poll cycle")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
