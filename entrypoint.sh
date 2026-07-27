#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for database..."
python - <<'PYEOF'
import sys
import time

import psycopg

from app.config import settings

dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

for attempt in range(1, 31):
    try:
        with psycopg.connect(dsn, connect_timeout=3):
            print("Database is ready.")
            break
    except Exception as exc:  # noqa: BLE001
        print(f"DB not ready ({attempt}/30): {exc}")
        time.sleep(2)
else:
    print("Database never became available", file=sys.stderr)
    sys.exit(1)
PYEOF

echo "Running migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"
