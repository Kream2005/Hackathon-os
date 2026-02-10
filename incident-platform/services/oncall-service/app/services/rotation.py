# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Service: Rotation logic — pure computation, no side effects.
"""

from datetime import datetime, timezone
from typing import Any, Optional


def compute_rotation(
    schedule: dict[str, Any],
) -> tuple[Optional[dict[str, str]], Optional[dict[str, str]]]:
    """
    Return (current_primary, current_secondary) based on rotation logic.
    Pure function — no I/O, no metrics, no logging.
    """
    members = schedule["members"]
    primary_members = [m for m in members if m["role"] == "primary"]
    secondary_members = [m for m in members if m["role"] == "secondary"]

    if not primary_members:
        return None, None

    now = datetime.now(timezone.utc)
    if schedule["rotation_type"] == "daily":
        rotation_index = now.timetuple().tm_yday
    elif schedule["rotation_type"] == "biweekly":
        rotation_index = now.isocalendar()[1] // 2
    else:  # weekly (default)
        rotation_index = now.isocalendar()[1]

    current_primary = primary_members[rotation_index % len(primary_members)]
    current_secondary = None
    if secondary_members:
        current_secondary = secondary_members[rotation_index % len(secondary_members)]

    return current_primary, current_secondary
