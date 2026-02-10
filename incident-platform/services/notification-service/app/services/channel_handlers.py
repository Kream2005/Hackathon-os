# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Channel delivery handlers — mock implementations."""
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def deliver_mock(incident_id: str, recipient: str, message: str, **kwargs) -> str:
    logger.info("[MOCK] Notified %s about incident %s: %s", recipient, incident_id, message)
    return "sent"


async def deliver_email(incident_id: str, recipient: str, message: str, **kwargs) -> str:
    logger.info("[MOCK EMAIL] To: %s | Subject: Incident %s | Body: %s", recipient, incident_id, message)
    return "sent"


async def deliver_slack(incident_id: str, recipient: str, message: str, **kwargs) -> str:
    logger.info("[MOCK SLACK] Channel/User: %s | Incident: %s | %s", recipient, incident_id, message)
    return "sent"


async def deliver_webhook(incident_id: str, recipient: str, message: str, severity: str = None, **kwargs) -> str:
    if not settings.WEBHOOK_URL:
        logger.info("[MOCK WEBHOOK] Notified %s about incident %s: %s", recipient, incident_id, message)
        return "sent"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(settings.WEBHOOK_URL, json={
                "incident_id": incident_id,
                "message": message,
                "recipient": recipient,
                "severity": severity,
            })
            if resp.status_code < 300:
                logger.info("Webhook delivered to %s for incident %s (status=%s)", settings.WEBHOOK_URL, incident_id, resp.status_code)
                return "sent"
            else:
                logger.warning("Webhook returned %s for incident %s", resp.status_code, incident_id)
                return "failed"
    except Exception as exc:
        logger.error("Webhook delivery failed: %s", exc)
        return "failed"


CHANNEL_HANDLERS = {
    "mock": deliver_mock,
    "email": deliver_email,
    "slack": deliver_slack,
    "webhook": deliver_webhook,
}
