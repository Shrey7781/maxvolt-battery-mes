from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session


def dedupe_by_keys(rows: list[dict], keys: list[str]) -> list[dict]:
    """Collapses rows sharing the same values for `keys`, keeping the last
    occurrence — 'latest wins', the same semantics as the upsert itself.

    Exposed separately (not just inlined in upsert_all) so callers can
    derive other per-request signals — e.g. the rework/NG judgment — from
    the same view of "what will actually be persisted" rather than from
    every raw record in the batch, which can disagree with it when a batch
    contains more than one record for the same natural key.
    """
    deduped: dict[tuple, dict] = {}
    for row in rows:
        key = tuple(row[c] for c in keys)
        deduped[key] = row
    return list(deduped.values())


def upsert_all(db: Session, model, rows: list[dict], conflict_cols: list[str]) -> None:
    """Idempotent bulk insert keyed on `conflict_cols`.

    Devices on the factory floor retry on network hiccups, so a resend of
    the same reading must succeed (and overwrite with the latest values)
    rather than fail as a duplicate. If a single incoming batch happens to
    contain more than one record for the same conflict key, Postgres would
    reject a single multi-row ON CONFLICT statement that touches the same
    row twice — so we de-duplicate first, keeping the last occurrence.
    """
    if not rows:
        return

    rows = dedupe_by_keys(rows, conflict_cols)

    stmt = pg_insert(model).values(rows)
    update_cols = {
        column.name: getattr(stmt.excluded, column.name)
        for column in model.__table__.columns
        if column.name not in conflict_cols and column.name not in ("id", "created_at", "updated_at")
    }
    update_cols["updated_at"] = func.now()

    stmt = stmt.on_conflict_do_update(index_elements=conflict_cols, set_=update_cols)
    db.execute(stmt)
