from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings
from app.security import API_KEY_HEADER


def rate_limit_key(request: Request) -> str:
    """Key by API key when present so devices sharing a NAT gateway don't
    throttle each other; falls back to remote IP for unauthenticated
    requests (which will be rejected anyway, but still shouldn't be able
    to hammer the endpoint)."""
    return request.headers.get(API_KEY_HEADER) or get_remote_address(request)


limiter = Limiter(key_func=rate_limit_key, default_limits=[f"{settings.rate_limit_per_minute}/minute"])
