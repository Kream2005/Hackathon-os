# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Repository package — re-exports IncidentRepository."""
from app.repositories.incident_repository import IncidentRepository

__all__ = ["IncidentRepository"]
