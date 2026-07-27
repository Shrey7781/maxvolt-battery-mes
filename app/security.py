import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.envelope import RTN, MESError
from app.models.auth import ApiKey

API_KEY_HEADER = "X-API-Key"


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def require_station_access(station: str):
    """Dependency factory: validates X-API-Key and its scope for `station`.

    Scoping is per-station (matching the router path slug) rather than a
    single shared credential, so a compromised or misbehaving device on one
    station cannot post data — or trigger rework routing — for another.
    """

    def dependency(request: Request, db: Session = Depends(get_db)) -> ApiKey:
        raw_key = request.headers.get(API_KEY_HEADER)
        if not raw_key:
            raise MESError(RTN.UNAUTHORIZED, f"Missing {API_KEY_HEADER} header")

        key_hash = hash_api_key(raw_key)
        api_key = db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash)).scalar_one_or_none()

        if api_key is None or not api_key.is_active:
            raise MESError(RTN.UNAUTHORIZED, "Invalid or inactive API key")

        if "*" not in api_key.allowed_stations and station not in api_key.allowed_stations:
            raise MESError(RTN.FORBIDDEN, f"API key '{api_key.device_name}' is not authorized for station '{station}'")

        api_key.last_used_at = datetime.now(timezone.utc)
        db.add(api_key)
        db.commit()
        return api_key

    return dependency
