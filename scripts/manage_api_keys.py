#!/usr/bin/env python3
"""Provision and manage per-device API keys.

Run inside the container, e.g.:

    docker compose exec api python scripts/manage_api_keys.py create \\
        --device-name "Cell Sorting Robot #1" --stations cell-sorting

    docker compose exec api python scripts/manage_api_keys.py list
    docker compose exec api python scripts/manage_api_keys.py revoke --id <uuid>

Station slugs match the router paths in openapi.yaml / app/routers/*.py:
cell-sorting, cell-module-binding, auto-stacking, polarity-detection,
laser-cleaning, laser-welding, module-eol-test, module-pack-binding,
liquid-cooling-airtightness, pack-eol-test, pack-airtightness.
Pass --stations "*" to allow every station.
"""

import argparse
import sys
import uuid

from app.database import SessionLocal
from app.models.auth import ApiKey
from app.security import generate_api_key, hash_api_key


def cmd_create(args: argparse.Namespace) -> None:
    raw_key = generate_api_key()
    stations = [s.strip() for s in args.stations.split(",") if s.strip()]

    with SessionLocal() as db:
        api_key = ApiKey(device_name=args.device_name, key_hash=hash_api_key(raw_key), allowed_stations=stations)
        db.add(api_key)
        db.commit()
        db.refresh(api_key)

    print("API key created — this is the only time the raw key is shown:")
    print(f"  id:              {api_key.id}")
    print(f"  device_name:     {api_key.device_name}")
    print(f"  allowed_stations:{api_key.allowed_stations}")
    print(f"  X-API-Key:       {raw_key}")


def cmd_list(args: argparse.Namespace) -> None:
    with SessionLocal() as db:
        keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
    if not keys:
        print("No API keys.")
        return
    for k in keys:
        status = "active" if k.is_active else "revoked"
        print(f"{k.id}  {status:8}  {k.device_name:30}  stations={k.allowed_stations}  last_used={k.last_used_at}")


def cmd_revoke(args: argparse.Namespace) -> None:
    with SessionLocal() as db:
        api_key = db.get(ApiKey, uuid.UUID(args.id))
        if api_key is None:
            print(f"No API key with id {args.id}", file=sys.stderr)
            sys.exit(1)
        api_key.is_active = False
        db.add(api_key)
        db.commit()
    print(f"Revoked {args.id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="Provision a new API key")
    p_create.add_argument("--device-name", required=True)
    p_create.add_argument("--stations", required=True, help='Comma-separated station slugs, or "*" for all')
    p_create.set_defaults(func=cmd_create)

    p_list = sub.add_parser("list", help="List API keys")
    p_list.set_defaults(func=cmd_list)

    p_revoke = sub.add_parser("revoke", help="Deactivate an API key")
    p_revoke.add_argument("--id", required=True)
    p_revoke.set_defaults(func=cmd_revoke)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
