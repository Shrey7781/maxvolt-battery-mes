# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See also `../CLAUDE.md` (one directory up) for the full project context: source documents, vendor
interface spec history, and the reasoning behind major architecture decisions (auth model, DB
credential handling, response envelope, etc.). This file covers day-to-day commands and
implementation-level structure specific to this `mes-backend/` service.

## Commands

Run the stack locally (Postgres on host port 5434, API on 8010 — remapped because 5432/8000 are
already used by other local services):

```bash
docker compose up -d --build
```

Migrations run automatically on container start (`entrypoint.sh` waits for the DB, then runs
`alembic upgrade head`). The `api` service mounts `./app`, `./alembic`, `./scripts` as volumes and
runs uvicorn with `--reload`, so code edits apply without rebuilding.

Provision a device API key (raw key is only shown once):

```bash
docker compose exec api python scripts/manage_api_keys.py create --device-name "..." --stations cell-sorting
docker compose exec api python scripts/manage_api_keys.py create --device-name "..." --stations "*"   # all stations
docker compose exec api python scripts/manage_api_keys.py list
docker compose exec api python scripts/manage_api_keys.py revoke --id <uuid>
```

Migrations (run inside the container, or locally against `DATABASE_URL`):

```bash
alembic upgrade head
alembic revision -m "description" --autogenerate   # review the generated migration before committing
```

Tests (run locally, not in Docker — needs a real Postgres reachable at `DATABASE_URL`; CI spins up
an ephemeral one, see `.github/workflows/backend-tests.yml`):

```bash
pip install -r requirements-dev.txt
alembic upgrade head            # against the test DB
pytest -v
pytest tests/test_cell_sorting.py -v            # single file
pytest tests/test_cell_sorting.py::test_name -v # single test
```

`tests/conftest.py` sets `DB_SECRET_ARN=""` and a local `DATABASE_URL` via `os.environ.setdefault`
**before any `app.*` import** — this must stay first in the file. `app/config.py`'s `Settings()`
runs at import time and defaults to a real production AWS Secrets Manager ARN when
`DB_SECRET_ARN` isn't set (see Architecture below), so tests must force it empty before `app.main`
or anything importing `app.config` is ever imported, or a test run will attempt to fetch real
production credentials.

There is no lint/format command configured in this repo (no ruff/black/flake8 config present).

## Architecture

### Response envelope — always HTTP 200

Every station endpoint returns HTTP 200; the real outcome is in the JSON body's `rtnCode`
(`app/envelope.py`, `RTN` enum): 200 success, 201 rework (an NG judgment was recorded — device
should route the physical unit to rework), 400/401/403/404/409/422/429/500 for various failures.
Only 200/201 are vendor-defined; the rest are this project's own extension. `main.py` registers
exception handlers that convert `MESError`, validation errors, `IntegrityError`, and rate-limit
errors into this envelope — **raise `MESError(RTN.X, "message")` from anywhere in request handling
to short-circuit to a proper response**, don't return error JSON directly from a route.

The one deliberate exception is `/healthz`, which returns real HTTP status codes (200/503) because
infra health checks (ALB, ECS) key off the status line, not the body.

### Request flow (every station router follows this shape)

Each endpoint in `app/routers/{cell,module,pack}.py` follows the same sequence — when adding a new
station endpoint, replicate this order. (`app/routers/work_order.py` is the one exception: steps 3
and 4 don't apply to it — see Data model below for why.)

1. Validate/normalize the request body via a Pydantic schema in `app/schemas/{cell,module,pack}.py`
   (built on shared types in `app/schemas/common.py` — `CodeStr`, `JudgmentStr`, `NonNegFloat`,
   `MesTimestamp`, `OptionalEmployeeCode`).
2. Convert each record to a dict, attach `api_key_id` (from the `require_station_access` dependency)
   and `raw_payload` (the full original record, for audit/debugging).
3. Run genealogy/reference checks (`app/services/genealogy.py`) — `ensure_*_exist` for FK
   existence, `ensure_*_sorted_ok`/`ensure_*_passed_eol` for upstream result gating, `ensure_*_not_rebound`
   for identity-reassignment protection. These raise `MESError` and must run **before** any DB write.
4. `register_operators` (`app/services/operators.py`) — auto-upserts `usercode`/`employee_code`
   into the `operators` master table (all stations except Auto Stacking, which has neither field).
5. `upsert_all` (`app/services/upsert.py`) — idempotent `INSERT ... ON CONFLICT DO UPDATE` keyed on
   the station's natural key(s). **Always call `dedupe_by_keys` (or reuse `upsert_all`'s
   deduplication) before deriving judgment/rtn info from the batch** — a single request can contain
   more than one record for the same natural key, and only the last one actually gets persisted.
6. `db.commit()`.
7. Compute `rtnCode`/`msg` via `rtn_for_judgments(*judgment_values)` (`app/services/judgment.py`) —
   pass every judgment column relevant to that station (a station can have several, e.g.
   `module-eol-test` has 5). Returns 201 if any value is `NG`.

### Data model

- One reading table per station in `app/models/{cell,module,pack}.py`, each upserted (never a full
  event history — a device retry overwrites in place, so each table reflects **latest state only**
  per natural key). Every reading table carries a nullable `api_key_id` FK and a `raw_payload` JSONB
  column holding the full original request record.
- Four master/identity tables in `app/models/entities.py` (`cells`, `modules`, `packs`,
  `operators`) enforce cross-station referential integrity via real Postgres FKs from every
  downstream reading table's natural-key column. `cells`/`modules`/`packs` are created as identities
  are first seen (by `cell-sorting`, `cell-module-binding`, `module-pack-binding` respectively) and
  additionally cache the latest pass/fail judgment needed for gating the next station
  (`Cell.pass_information`, `Module.eol_pass_information`) — see `genealogy.py`'s module docstring
  for exactly which binding points gate on result vs. mere existence.
- `operators` auto-registers every `usercode` seen, never blocks ingestion (no `ensure_operator_exists`
  check exists, unlike cells/modules/packs), and preserves a previously-known `operator_name` if a
  later submission omits `employee_code` (via `COALESCE` in the upsert).
- `work_orders` (`app/models/work_order.py`, station slug `work-order`) is **not** in the vendor's
  interface spec — it's this project's own addition for vendor-pushed work order data, POSTed
  manually from one or two station devices (identity/slug ownership not finalized yet as of
  2026-09-02, but the auth scoping already works the same as every other station once a real device
  is provisioned). One row per `pack_barcode` (the upsert conflict key), carrying `work_order_id`
  (one work order can span multiple `batch_number`s — production sometimes splits an order across
  several batches), batch-level fields (`product_name`, `series_configuration`,
  `parallel_configuration`, `category`, `quantity`, `batch_number`), `current_status` (closed set —
  `completed`/`pending` only, case-insensitive on input; no OK/NG judgment, so this endpoint always
  returns rtnCode 200, never 201/rework), and optional `actual_time`/`completion_time`. Deliberately
  has **no** genealogy check against `packs.pack_code` and **no** operator field/`register_operators`
  call (like Auto Stacking) — a work order can arrive before, after, or without any corresponding
  `module-pack-binding` row. `_ensure_barcodes_not_rebound` in `app/routers/work_order.py` (mirrors
  `genealogy.ensure_cells_not_rebound`) rejects (409) reposting a `pack_barcode` under a different
  `work_order_id`/`batch_number` than it was first recorded under — without it, since `pack_barcode`
  alone is the upsert key, a reassigned barcode would silently vanish from its original batch's
  summary counts with no error (found during end-to-end verification, 2026-09-02).

  Two read-only rollups (`app/services/work_order_summary.py`), both requiring the same `work-order`
  station scope: `GET /stations/work-order/batches/{batch_number}/summary` and
  `GET /stations/work-order/orders/{work_order_id}/summary` (the latter sums each distinct batch's
  own `quantity` for `target_quantity` — not per pack-row, which would double-count). Both return
  `reported_quantity`/`completed_quantity`/`pending_quantity`/`good_quantity`/`rejected_quantity`.
  A pack counts as **rejected** if pack-eol-test, pack-airtightness, or liquid-cooling-airtightness
  recorded NG for its `pack_code` (assumed == `pack_barcode`), **or** if any cell bound into one of
  its modules (via module-pack-binding → cell-module-binding) has `Cell.pass_information == NG` —
  including a cell that was OK when bound but got flipped NG by a later re-sort. Deliberately scoped
  to cell + pack level only (no module-level judgments considered), per request. An unmatched
  `pack_barcode` (never bound to a real pack on the line) contributes no NG signal and counts good.

### Auth & rate limiting

`X-API-Key` header, SHA-256 hashed at rest (`app/security.py`), scoped to a list of station slugs
(or `"*"`) via `ApiKey.allowed_stations`. `require_station_access(station)` is a dependency
factory — use it in every new route, parameterized with that route's station slug (matching the
router path segment). Rate limiting (`app/rate_limit.py`, slowapi) keys by `X-API-Key` when
present, falling back to remote IP, so devices sharing a NAT gateway don't throttle each other.

### Config / credentials (`app/config.py`)

`Settings()` executes at **import time**. `database_url` defaults to a local dev connection string,
but `db_secret_arn` defaults to a **real production AWS Secrets Manager ARN** and `environment`
defaults to `"production"` — this is a deliberate (if risky) stopgap documented in `../CLAUDE.md`
because there's currently no per-environment env var access on the ECS task definition. Local dev's
`.env` and CI's workflow env both explicitly set `DB_SECRET_ARN=` to override this back off — **any
new test setup or local script that imports `app.config` (directly or transitively) must ensure
`DB_SECRET_ARN` is set to empty before that import happens**, exactly as `tests/conftest.py` does.
When `db_secret_arn` is set, `database_url` is overwritten by a live fetch from Secrets Manager at
import time (`_database_url_from_secret`) — the database name always comes from `DB_NAME`, never
from the secret's own `dbname` field, because the production secret is shared across unrelated
apps.

### Adding a new station endpoint

1. Add the station slug to `tests/stations.py::STATIONS` and to the docstring list in
   `scripts/manage_api_keys.py`.
2. Add a Pydantic schema in the relevant `app/schemas/*.py` (reuse `common.py` types).
3. Add a model in the relevant `app/models/*.py` with a `UniqueConstraint` matching the station's
   natural key, an `api_key_id` FK, and a `raw_payload` JSONB column.
4. Add an Alembic migration for the new table (`alembic revision --autogenerate`, then review).
5. Add the route in the relevant `app/routers/*.py`, following the six-step flow above.
6. Add tests following the existing pattern in `tests/test_*.py` (one API key per station via the
   `api_keys` fixture, `unique_code` fixture for natural keys to avoid cross-test collisions).
