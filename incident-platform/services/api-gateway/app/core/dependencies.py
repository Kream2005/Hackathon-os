# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Dependency injection — HTTP client and proxy service singletons."""
import httpx
from app.services.proxy_service import ProxyService
from app.services.auth_service import AuthService

_http_client: httpx.AsyncClient | None = None
_proxy_service: ProxyService | None = None
_auth_service = AuthService()


def init_http_client():
    global _http_client, _proxy_service
    _http_client = httpx.AsyncClient(timeout=10.0)
    _proxy_service = ProxyService(_http_client)


async def close_http_client():
    global _http_client
    if _http_client:
        await _http_client.aclose()


def get_http_client() -> httpx.AsyncClient:
    assert _http_client is not None
    return _http_client


def get_proxy_service() -> ProxyService:
    assert _proxy_service is not None
    return _proxy_service


def get_auth_service() -> AuthService:
    return _auth_service
