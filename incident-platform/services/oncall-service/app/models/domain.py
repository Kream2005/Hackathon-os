# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Domain models — pure data structures, NO FastAPI dependency.
"""

from pydantic import BaseModel, Field
from typing import Optional


class Member(BaseModel):
    """A single on-call team member."""
    name: str = Field(..., min_length=1, max_length=255, description="Member name")
    email: str = Field(..., min_length=1, max_length=255, description="Member email")
    role: str = Field(
        ..., pattern="^(primary|secondary)$", description="Role: primary or secondary"
    )
