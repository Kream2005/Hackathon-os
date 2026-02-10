# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
HTTP client for Incident Management service — fire-and-forget.
"""

import httpx
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class IncidentClient:
    """Communicates with the Incident Management Service."""

    def create_incident(self, service: str, severity: str, message: str) -> Optional[str]:
        """Ask the Incident Management Service to create the incident."""
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(
                    f"{settings.INCIDENT_MANAGEMENT_URL}/api/v1/incidents",
                    json={
                        "title": f"[{severity.upper()}] {service}: {message[:120]}",
                        "service": service,
                        "severity": severity,
                    },
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return data.get("id") or data.get("incident_id")
                logger.warning("Incident-management returned %s: %s", resp.status_code, resp.text[:200])
        except Exception as exc:
            logger.warning("Incident-management unreachable: %s", exc)
        return None
