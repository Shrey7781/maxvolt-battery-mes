from sqlalchemy import bindparam, select, update
from sqlalchemy.orm import Session

from app.envelope import RTN, MESError
from app.models.entities import Cell, Module, Pack
from app.models.module import CellModuleBinding
from app.models.pack import LiquidCoolingAirtightnessReading, ModulePackBinding
from app.services.upsert import upsert_all

"""Cross-station referential validation.

Each 'ensure_*_exist' call is a required-upstream-station gate: e.g. a
module can't be stacked, cleaned, welded, EOL-tested, or bound to a pack
unless it was first created via cell-module-binding. Each 'register_*'
call is what creates that identity in the first place: cells at
cell-sorting, modules at cell-module-binding, packs at
liquid-cooling-airtightness (the first pack station — moved ahead of
module-pack-binding in the vendor's 2026-10 spec revision; module-pack-
binding now requires the pack to exist instead of creating it). Only an OK
liquid cooling result carries a pack_code, so only a plate that passed
creates a pack.

On top of existence, two binding points also gate on the upstream result,
not just presence — an NG part shouldn't advance to the next assembly
step even though its identity is known:
  - cell-module-binding requires the cell's latest cell-sorting result to
    be OK (ensure_cells_sorted_ok).
  - module-pack-binding requires the module to have completed
    module-eol-test with an OK result (ensure_modules_passed_eol), and the
    pack's latest liquid-cooling-airtightness result to be OK
    (ensure_packs_passed_liquid_cooling).
Intermediate module stations (auto-stacking, polarity-detection,
laser-cleaning, laser-welding) are not sequenced against each other here
— there's no fixed required order between them being asserted, only that
the module exists.
"""


def _check_exist(db: Session, column, codes: list[str], hint: str) -> None:
    codes = sorted(set(codes))
    if not codes:
        return
    found = set(db.execute(select(column).where(column.in_(codes))).scalars())
    missing = [c for c in codes if c not in found]
    if missing:
        raise MESError(RTN.REFERENCE_NOT_FOUND, f"Unknown {', '.join(missing)} — {hint}")


def ensure_cells_exist(db: Session, cell_codes: list[str]) -> None:
    _check_exist(db, Cell.cell_code, cell_codes, "not recorded by cell-sorting")


def ensure_modules_exist(db: Session, mod_codes: list[str]) -> None:
    _check_exist(db, Module.mod_code, mod_codes, "not recorded by cell-module-binding")


def ensure_packs_exist(db: Session, pack_codes: list[str]) -> None:
    _check_exist(db, Pack.pack_code, pack_codes, "not recorded by liquid-cooling-airtightness")


def ensure_cells_sorted_ok(db: Session, cell_codes: list[str]) -> None:
    """Assumes ensure_cells_exist already passed for these codes."""
    codes = sorted(set(cell_codes))
    if not codes:
        return
    rows = db.execute(select(Cell.cell_code, Cell.pass_information).where(Cell.cell_code.in_(codes))).all()
    failed = [code for code, result in rows if result != "OK"]
    if failed:
        raise MESError(
            RTN.PRECONDITION_FAILED,
            f"Cell(s) failed sorting (NG), cannot bind to a module: {', '.join(sorted(failed))}",
        )


def ensure_modules_passed_eol(db: Session, mod_codes: list[str]) -> None:
    """Assumes ensure_modules_exist already passed for these codes."""
    codes = sorted(set(mod_codes))
    if not codes:
        return
    rows = db.execute(select(Module.mod_code, Module.eol_pass_information).where(Module.mod_code.in_(codes))).all()
    found = dict(rows)
    problems = []
    for code in codes:
        result = found.get(code)
        if result is None:
            problems.append(f"{code} (no module-eol-test record)")
        elif result != "OK":
            problems.append(f"{code} (module-eol-test result NG)")
    if problems:
        raise MESError(
            RTN.PRECONDITION_FAILED,
            f"Module(s) not eligible for pack binding: {', '.join(problems)}",
        )


def ensure_packs_passed_liquid_cooling(db: Session, pack_codes: list[str]) -> None:
    """Assumes ensure_packs_exist already passed for these codes. A pack
    only gets created by an OK liquid cooling result, but its plate can be
    retested NG afterwards (the row keeps its pack_code), and packs created
    by module-pack-binding before the 2026-10 station reorder have no liquid
    cooling record at all — both are blocked, same as the module EOL gate."""
    codes = sorted(set(pack_codes))
    if not codes:
        return
    found = dict(
        db.execute(
            select(LiquidCoolingAirtightnessReading.pack_code, LiquidCoolingAirtightnessReading.result).where(
                LiquidCoolingAirtightnessReading.pack_code.in_(codes)
            )
        ).all()
    )
    problems = []
    for code in codes:
        result = found.get(code)
        if result is None:
            problems.append(f"{code} (no liquid-cooling-airtightness record)")
        elif result != "OK":
            problems.append(f"{code} (liquid-cooling-airtightness result NG)")
    if problems:
        raise MESError(
            RTN.PRECONDITION_FAILED,
            f"Pack(s) not eligible for module binding: {', '.join(problems)}",
        )


def ensure_cells_not_rebound(db: Session, rows: list[dict]) -> None:
    """A cell already bound to a module can be resubmitted for that SAME
    module (idempotent retry on a network blip — upsert_all overwrites in
    place as usual), but binding it to a DIFFERENT module is rejected
    rather than silently overwritten: a physical cell can't move to a
    different module after welding, so a change in partner code is far
    more likely an operator/data error than a legitimate rebind.
    """
    by_cell = {r["cell_code"]: r["mod_code"] for r in rows}
    if not by_cell:
        return
    existing = dict(
        db.execute(
            select(CellModuleBinding.cell_code, CellModuleBinding.mod_code).where(
                CellModuleBinding.cell_code.in_(by_cell.keys())
            )
        ).all()
    )
    conflicts = [
        f"{cell_code} (already bound to module {existing[cell_code]}, not {new_mod_code})"
        for cell_code, new_mod_code in by_cell.items()
        if cell_code in existing and existing[cell_code] != new_mod_code
    ]
    if conflicts:
        raise MESError(RTN.DUPLICATE, f"Cell(s) already bound to a different module: {', '.join(sorted(conflicts))}")


def ensure_modules_not_rebound(db: Session, rows: list[dict]) -> None:
    """Same protection as ensure_cells_not_rebound, one level up: a module
    already bound to a pack can be resubmitted for that SAME pack, but not
    silently reassigned to a different one.
    """
    by_module = {r["mod_code"]: r["pack_code"] for r in rows}
    if not by_module:
        return
    existing = dict(
        db.execute(
            select(ModulePackBinding.mod_code, ModulePackBinding.pack_code).where(
                ModulePackBinding.mod_code.in_(by_module.keys())
            )
        ).all()
    )
    conflicts = [
        f"{mod_code} (already bound to pack {existing[mod_code]}, not {new_pack_code})"
        for mod_code, new_pack_code in by_module.items()
        if mod_code in existing and existing[mod_code] != new_pack_code
    ]
    if conflicts:
        raise MESError(RTN.DUPLICATE, f"Module(s) already bound to a different pack: {', '.join(sorted(conflicts))}")


def ensure_plates_not_rebound(db: Session, rows: list[dict]) -> None:
    """Same protection for liquid cooling plates: a plate's barcode is
    stuck on it and the plate isn't swapped between packs, so once a
    cooled_code has a pack_code, a later result for that plate naming a
    DIFFERENT pack is rejected. Rows without a pack_code (NG results) never
    conflict — they leave the stored pack_code as it is.
    """
    by_plate = {r["cooled_code"]: r["pack_code"] for r in rows if r.get("pack_code") is not None}
    if not by_plate:
        return
    existing = dict(
        db.execute(
            select(LiquidCoolingAirtightnessReading.cooled_code, LiquidCoolingAirtightnessReading.pack_code).where(
                LiquidCoolingAirtightnessReading.cooled_code.in_(by_plate.keys()),
                LiquidCoolingAirtightnessReading.pack_code.is_not(None),
            )
        ).all()
    )
    conflicts = [
        f"{cooled_code} (already bound to pack {existing[cooled_code]}, not {new_pack_code})"
        for cooled_code, new_pack_code in by_plate.items()
        if cooled_code in existing and existing[cooled_code] != new_pack_code
    ]
    if conflicts:
        raise MESError(
            RTN.DUPLICATE, f"Liquid cooling plate(s) already bound to a different pack: {', '.join(sorted(conflicts))}"
        )


def ensure_packs_have_one_plate(db: Session, rows: list[dict]) -> None:
    """The reverse of ensure_plates_not_rebound: a pack has exactly one
    liquid cooling plate, so a pack_code already recorded with one
    cooled_code can't be reposted with a DIFFERENT one — whether that other
    plate is already stored or in the same batch. Without this, the
    uq_liquid_cooling_pack constraint would still block it, but through the
    generic duplicate-key handler, which can't name the plates involved.
    Expects rows already deduped by cooled_code, all carrying a pack_code.
    """
    by_pack: dict[str, set[str]] = {}
    for r in rows:
        by_pack.setdefault(r["pack_code"], set()).add(r["cooled_code"])
    if not by_pack:
        return
    conflicts = [
        f"{pack_code} (sent with plates {', '.join(sorted(plates))} in one batch)"
        for pack_code, plates in by_pack.items()
        if len(plates) > 1
    ]
    existing = dict(
        db.execute(
            select(LiquidCoolingAirtightnessReading.pack_code, LiquidCoolingAirtightnessReading.cooled_code).where(
                LiquidCoolingAirtightnessReading.pack_code.in_(by_pack.keys())
            )
        ).all()
    )
    conflicts += [
        f"{pack_code} (already has plate {existing[pack_code]}, not {next(iter(plates))})"
        for pack_code, plates in by_pack.items()
        if len(plates) == 1 and pack_code in existing and existing[pack_code] not in plates
    ]
    if conflicts:
        raise MESError(
            RTN.DUPLICATE, f"Pack(s) already have a different liquid cooling plate: {', '.join(sorted(conflicts))}"
        )


def ensure_pack_slots_available(db: Session, rows: list[dict]) -> None:
    """`module_pack_bindings` has a second unique constraint beyond the
    upsert's own conflict key (mod_code): (pack_code, mod_index) — a slot
    within a pack can only be occupied by one module. Without this check, a
    second, different module claiming an already-taken slot hits that
    constraint at the DB level and falls through to the generic duplicate-
    key handler, which can't say which slot collided. Check explicitly
    first so the error names the slot and the module that already holds
    it. A resubmission of the SAME module for the SAME slot (retry) is
    unaffected — ensure_modules_not_rebound covers that identity already.
    """
    by_slot = {(r["pack_code"], r["mod_index"]): r["mod_code"] for r in rows}
    if not by_slot:
        return
    pack_codes = {slot[0] for slot in by_slot}
    existing = {
        (pack_code, mod_index): mod_code
        for pack_code, mod_index, mod_code in db.execute(
            select(ModulePackBinding.pack_code, ModulePackBinding.mod_index, ModulePackBinding.mod_code).where(
                ModulePackBinding.pack_code.in_(pack_codes)
            )
        ).all()
    }
    conflicts = [
        f"{pack_code} slot {mod_index} (already occupied by module {existing[(pack_code, mod_index)]}, not {new_mod_code})"
        for (pack_code, mod_index), new_mod_code in by_slot.items()
        if (pack_code, mod_index) in existing and existing[(pack_code, mod_index)] != new_mod_code
    ]
    if conflicts:
        raise MESError(
            RTN.DUPLICATE, f"Pack slot(s) already occupied by a different module: {', '.join(sorted(conflicts))}"
        )


def register_cells(db: Session, rows: list[dict]) -> None:
    entity_rows = [
        {
            "cell_code": r["cell_code"],
            "proline_code": r["proline_code"],
            "first_station_code": r["station_code"],
            "pass_information": r["pass_information"],
        }
        for r in rows
    ]
    upsert_all(db, Cell, entity_rows, conflict_cols=["cell_code"])


def register_modules(db: Session, rows: list[dict]) -> None:
    entity_rows = [
        {"mod_code": r["mod_code"], "proline_code": r["proline_code"], "first_station_code": r["station_code"]}
        for r in rows
    ]
    upsert_all(db, Module, entity_rows, conflict_cols=["mod_code"])


def register_packs(db: Session, rows: list[dict]) -> None:
    entity_rows = [
        {"pack_code": r["pack_code"], "proline_code": r["proline_code"], "first_station_code": r["station_code"]}
        for r in rows
    ]
    upsert_all(db, Pack, entity_rows, conflict_cols=["pack_code"])


_mark_eol_stmt = (
    # Built against the raw Table (not the mapped class) so this is a plain
    # Core UPDATE...WHERE — the ORM-enabled form of update(Module) forces
    # SQLAlchemy 2.0's "bulk UPDATE by primary key" path, which requires
    # every params dict to carry the PK and doesn't fit a WHERE-by-natural-key
    # executemany like this one.
    update(Module.__table__)
    .where(Module.mod_code == bindparam("_mod_code"))
    .values(eol_pass_information=bindparam("_result"))
)


def mark_module_eol_result(db: Session, rows: list[dict]) -> None:
    """Caches each module's latest module-eol-test judgment onto its master
    row, so module-pack-binding can gate on it without re-querying the
    (much larger) module_eol_test_readings table."""
    dedup = {r["mod_code"]: r["pass_information"] for r in rows}
    params = [{"_mod_code": mod_code, "_result": result} for mod_code, result in dedup.items()]
    db.execute(_mark_eol_stmt, params)
