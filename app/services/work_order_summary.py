from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Cell
from app.models.module import CellModuleBinding
from app.models.pack import LiquidCoolingAirtightnessReading, ModulePackBinding, PackAirtightnessReading, PackEolTestReading
from app.models.work_order import WorkOrder

"""Good/rejected yield for a work order batch, or for a whole work order
(one work_order_id can span multiple batch_numbers — production sometimes
splits one order across several batches).

A pack (identified by pack_barcode, taken to be the same value as pack_code
elsewhere on the line — see the Work Order note in ../../CLAUDE.md) is
'rejected' if an NG shows up anywhere in its quality chain:
  - pack-level: pack-eol-test, pack-airtightness, or liquid-cooling-
    airtightness recorded NG for that pack_code.
  - cell-level: any cell bound (via module-pack-binding -> cell-module-
    binding) into one of that pack's modules failed cell-sorting.
No module-level judgments (auto-stacking/polarity/cleaning/welding/module-
eol-test) are considered — scoped to cell and pack level only, by request.

This is a pure read/report computation: it does not gate ingestion and does
not require pack_barcode to exist anywhere else on the line (an unmatched
barcode simply contributes no NG signal and counts as good).
"""


def _pack_level_ng_codes(db: Session, pack_codes: list[str]) -> set[str]:
    ng: set[str] = set()
    for model, judgment_col in (
        (PackEolTestReading, PackEolTestReading.pass_information),
        (PackAirtightnessReading, PackAirtightnessReading.result),
        (LiquidCoolingAirtightnessReading, LiquidCoolingAirtightnessReading.result),
    ):
        rows = db.execute(
            select(model.pack_code).where(model.pack_code.in_(pack_codes), judgment_col == "NG")
        ).scalars()
        ng.update(rows)
    return ng


def _cell_level_ng_pack_codes(db: Session, pack_codes: list[str]) -> set[str]:
    bindings = db.execute(
        select(ModulePackBinding.pack_code, ModulePackBinding.mod_code).where(
            ModulePackBinding.pack_code.in_(pack_codes)
        )
    ).all()
    if not bindings:
        return set()

    mod_codes = {mod_code for _, mod_code in bindings}
    cell_bindings = db.execute(
        select(CellModuleBinding.mod_code, CellModuleBinding.cell_code).where(
            CellModuleBinding.mod_code.in_(mod_codes)
        )
    ).all()
    if not cell_bindings:
        return set()

    cell_codes = {cell_code for _, cell_code in cell_bindings}
    ng_cells = set(
        db.execute(select(Cell.cell_code).where(Cell.cell_code.in_(cell_codes), Cell.pass_information == "NG")).scalars()
    )
    if not ng_cells:
        return set()

    cells_by_mod: dict[str, set[str]] = {}
    for mod_code, cell_code in cell_bindings:
        cells_by_mod.setdefault(mod_code, set()).add(cell_code)

    ng_packs: set[str] = set()
    for pack_code, mod_code in bindings:
        if cells_by_mod.get(mod_code, set()) & ng_cells:
            ng_packs.add(pack_code)
    return ng_packs


def _summarize(db: Session, work_orders: list[WorkOrder], target_quantity: int) -> dict:
    pack_barcodes = [wo.pack_barcode for wo in work_orders]
    rejected_barcodes = _pack_level_ng_codes(db, pack_barcodes) | _cell_level_ng_pack_codes(db, pack_barcodes)

    reported_quantity = len(work_orders)
    rejected_quantity = sum(1 for wo in work_orders if wo.pack_barcode in rejected_barcodes)
    completed_quantity = sum(1 for wo in work_orders if wo.current_status == "completed")

    return {
        "target_quantity": target_quantity,
        "reported_quantity": reported_quantity,
        "completed_quantity": completed_quantity,
        "pending_quantity": reported_quantity - completed_quantity,
        "good_quantity": reported_quantity - rejected_quantity,
        "rejected_quantity": rejected_quantity,
    }


def compute_batch_summary(db: Session, batch_number: str) -> dict | None:
    work_orders = db.execute(select(WorkOrder).where(WorkOrder.batch_number == batch_number)).scalars().all()
    if not work_orders:
        return None

    summary = _summarize(db, work_orders, target_quantity=work_orders[0].quantity)
    summary["batch_number"] = batch_number
    return summary


def compute_work_order_summary(db: Session, work_order_id: str) -> dict | None:
    """Rolls up every batch sharing this work_order_id. target_quantity is
    the sum of each distinct batch's own target quantity (not per-pack row,
    which would double-count every pack in a batch)."""
    work_orders = db.execute(select(WorkOrder).where(WorkOrder.work_order_id == work_order_id)).scalars().all()
    if not work_orders:
        return None

    batch_target_quantity: dict[str, int] = {}
    for wo in work_orders:
        batch_target_quantity[wo.batch_number] = wo.quantity

    summary = _summarize(db, work_orders, target_quantity=sum(batch_target_quantity.values()))
    summary["work_order_id"] = work_order_id
    summary["batch_count"] = len(batch_target_quantity)
    return summary
