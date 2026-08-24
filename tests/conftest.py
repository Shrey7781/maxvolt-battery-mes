import os
import uuid

# Must run before any `app.*` import: app/config.py's Settings() executes
# at import time and defaults to a REAL production AWS Secrets Manager ARN
# when DB_SECRET_ARN isn't explicitly overridden (see the comment there).
# Tests — in CI or run locally — must never fetch real production
# credentials. setdefault() so an explicit CI-provided value always wins;
# this is only the safety net for local/uncofigured runs.
os.environ.setdefault("DB_SECRET_ARN", "")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://mes:mes@localhost:5432/mes_test")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")
os.environ.setdefault("LOG_LEVEL", "WARNING")

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.auth import ApiKey
from app.security import generate_api_key, hash_api_key
from tests.stations import STATIONS


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def api_keys():
    """One API key per station, scoped to that station only — mirrors the
    real per-station isolation model (app/security.py). Inserted directly
    into the test database rather than via scripts/manage_api_keys.py to
    avoid shelling out; the test DB is assumed already migrated to head
    (the CI workflow runs `alembic upgrade head` before pytest)."""
    keys = {}
    with SessionLocal() as db:
        for station in STATIONS:
            raw = generate_api_key()
            db.add(
                ApiKey(
                    device_name=f"pytest - {station}",
                    key_hash=hash_api_key(raw),
                    allowed_stations=[station],
                    is_active=True,
                )
            )
            keys[station] = raw
        db.commit()
    return keys


@pytest.fixture
def unique_code():
    """Returns a function generating a fresh natural-key code per call, so
    tests never collide with each other or with prior runs against a
    persistent database."""

    def _make(prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:10]}"

    return _make
