# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Authentication service — API key and user credential validation."""
from typing import Dict, Any
from fastapi import HTTPException
from app.core.config import settings


class AuthService:
    def login(self, username: str, password: str) -> Dict[str, Any]:
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password required")
        expected = settings.USER_CREDENTIALS.get(username)
        if expected is None or expected != password:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        return {
            "api_key": settings.LOGIN_API_KEY,
            "username": username,
            "message": "Login successful",
        }

    def validate_api_key(self, api_key: str) -> bool:
        return api_key in settings.API_KEYS
