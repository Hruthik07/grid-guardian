import logging
import os

logger = logging.getLogger("grid_guardian.sms")


def send_sms(to_phone: str, body: str) -> None:
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_phone = os.environ.get("TWILIO_FROM_NUMBER")
    if not (account_sid and auth_token and from_phone):
        logger.warning("Twilio not configured; skipping SMS to %s", to_phone)
        return
    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        client.messages.create(to=to_phone, from_=from_phone, body=body)
    except Exception:
        logger.exception("Failed to send SMS to %s", to_phone)
