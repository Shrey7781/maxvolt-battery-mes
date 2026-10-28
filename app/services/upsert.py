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


def upsert_all(db: Session, model, rows: list[dict], conflict_cols: list[str], conflict_target: list | None = None) -> None:
    """Idempotent bulk insert keyed on `conflict_cols`.

    Devices on the factory floor retry on network hiccups, so a resend of
    the same reading must succeed (and overwrite with the latest values)
    rather than fail as a duplicate. If a single incoming batch happens to
    contain more than one record for the same conflict key, Postgres would
    reject a single multi-row ON CONFLICT statement that touches the same
    row twice — so we de-duplicate first, keeping the last occurrence.

    On conflict, only the columns actually supplied in `rows` are
    overwritten — a column the caller doesn't pass keeps its stored value
    rather than being reset to its insert default. This matters for master
    rows written by more than one station: register_modules (cell-module-
    binding) doesn't supply Module.eol_pass_information, which is set
    separately by module-eol-test, so a binding retry or a late extra cell
    for an already-tested module must not wipe that EOL result (it used to,
    which made module-pack-binding then reject the module with 422).

    `conflict_target` overrides the ON CONFLICT target for tables whose
    unique index is on an expression of `conflict_cols` rather than the bare
    columns — e.g. [Model.mod_code, func.md5(Model.col_coord)] for the long
    coordinate columns in app/models/module.py. Deduplication and the
    excluded-from-update set still go by `conflict_cols`.
    """
    if not rows:
        return

    rows = dedupe_by_keys(rows, conflict_cols)

    # A multi-row VALUES insert requires every row to carry the same keys, so
    # the first row's keys are the supplied set for the whole batch.
    supplied = rows[0].keys()
    stmt = pg_insert(model).values(rows)
    update_cols = {
        column.name: getattr(stmt.excluded, column.name)
        for column in model.__table__.columns
        if column.name in supplied
        and column.name not in conflict_cols
        and column.name not in ("id", "created_at", "updated_at")
    }
    update_cols["updated_at"] = func.now()

    stmt = stmt.on_conflict_do_update(index_elements=conflict_target or conflict_cols, set_=update_cols)
    db.execute(stmt)
