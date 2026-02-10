# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""HTTP client to query the on-call service."""
from typing import Any, Dict, Optional
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OncallClient:
    def get_current(self, team: str) -> Optional[Dict[str, Any]]:
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(
                    f"{settings.ONCALL_SERVICE_URL}/api/v1/oncall/current",
                    params={"team": team},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as exc:
            logger.warning("On-call service unreachable: %s", exc)
        return None
