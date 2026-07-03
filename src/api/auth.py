import hmac

from fastapi import Request
from fastapi.responses import JSONResponse

from src.config import settings


def _extract_token(request: Request) -> str:
    api_token = request.headers.get("X-API-Token", "").strip()
    if api_token:
        return api_token

    authorization = request.headers.get("Authorization", "").strip()
    if not authorization:
        return ""

    scheme, _, value = authorization.partition(" ")
    if scheme.lower() == "bearer" and value:
        return value.strip()
    return authorization


async def verify_token_middleware(request: Request, call_next):
    if not settings.token_auth_enabled or request.method == "OPTIONS":
        return await call_next(request)

    expected_token = settings.api_token.strip()
    if not expected_token:
        return JSONResponse(
            status_code=500,
            content={"detail": "Token authentication is enabled but API_TOKEN is not configured."},
        )

    actual_token = _extract_token(request)
    if not actual_token or not hmac.compare_digest(actual_token, expected_token):
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await call_next(request)
