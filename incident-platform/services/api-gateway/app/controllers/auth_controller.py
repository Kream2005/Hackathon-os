# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Controller: Authentication — login endpoint."""
from fastapi import APIRouter, Request, HTTPException
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1", tags=["Auth"])
_auth_service = AuthService()


@router.post("/auth/login")
async def login(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    username = body.get("username", "").strip()
    password = body.get("password", "")
    return _auth_service.login(username, password)
