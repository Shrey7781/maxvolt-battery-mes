from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.entities import Operator


def register_operators(db: Session, rows: list[dict]) -> None:
    """Auto-registers every `usercode` seen in a batch into the operators
    master table, purely for traceability — never blocks ingestion, no
    pre-provisioning required (unlike ensure_cells_exist/ensure_modules_exist
    in genealogy.py, there is no ensure_operator_exists).

    If the same operator_code recurs later without a name — 5 of the 11
    stations don't send employee_code at all, and it's optional everywhere
    it does appear — the previously known name is preserved rather than
    being overwritten with null.
    """
    dedup: dict[str, dict] = {}
    for r in rows:
        code = r.get("usercode")
        if not code:
            continue
        name = r.get("employee_code")
        if code in dedup:
            dedup[code]["operator_name"] = name or dedup[code]["operator_name"]
        else:
            dedup[code] = {
                "operator_code": code,
                "operator_name": name,
                "first_station_code": r.get("station_code"),
            }

    if not dedup:
        return

    stmt = pg_insert(Operator).values(list(dedup.values()))
    stmt = stmt.on_conflict_do_update(
        index_elements=["operator_code"],
        set_={
            # Keep the previously known name if this submission didn't
            # include one, instead of clobbering it with null.
            "operator_name": func.coalesce(stmt.excluded.operator_name, Operator.operator_name),
            "updated_at": func.now(),
        },
    )
    db.execute(stmt)
