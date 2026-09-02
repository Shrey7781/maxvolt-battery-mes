from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.envelope import RTN, MESError, StandardResponse
from app.models.work_order import WorkOrder
from app.schemas.work_order import WorkOrderRequest
from app.security import require_station_access
from app.services.judgment import rtn_for_judgments
from app.services.upsert import upsert_all
from app.services.work_order_summary import compute_batch_summary, compute_work_order_summary

router = APIRouter(prefix="/stations", tags=["Work Order"])

STATION = "work-order"


def _ensure_barcodes_not_rebound(db: Session, rows: list[dict]) -> None:
    """pack_barcode is the sole upsert key (app/models/work_order.py) —
    batch_number/work_order_id are not part of it. Without this guard, a
    barcode reposted under a different batch/work order would silently move
    there, and the original batch's summary would drop it with no error
    (confirmed live during verification). A resubmission under the SAME
    work_order_id + batch_number is still a normal idempotent retry —
    upsert_all overwrites it in place as usual. Mirrors
    genealogy.ensure_cells_not_rebound / ensure_modules_not_rebound."""
    barcodes = [r["pack_barcode"] for r in rows]
    if not barcodes:
        return
    existing = {
        pack_barcode: (work_order_id, batch_number)
        for pack_barcode, work_order_id, batch_number in db.execute(
            select(WorkOrder.pack_barcode, WorkOrder.work_order_id, WorkOrder.batch_number).where(
                WorkOrder.pack_barcode.in_(barcodes)
            )
        ).all()
    }
    conflicts = []
    for r in rows:
        prior = existing.get(r["pack_barcode"])
        if prior and prior != (r["work_order_id"], r["batch_number"]):
            prior_wo, prior_batch = prior
            conflicts.append(
                f"{r['pack_barcode']} (already recorded under work_order_id={prior_wo!r} "
                f"batch_number={prior_batch!r}, not {r['work_order_id']!r}/{r['batch_number']!r})"
            )
    if conflicts:
        raise MESError(
            RTN.DUPLICATE, f"Pack barcode(s) already recorded under a different work order/batch: {', '.join(sorted(conflicts))}"
        )


@router.post("/work-order/data", response_model=StandardResponse)
def upload_work_order(
    payload: WorkOrderRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access(STATION)),
):
    rows = []
    for record in payload.productionDataList:
        data = record.model_dump()
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    _ensure_barcodes_not_rebound(db, rows)
    upsert_all(db, WorkOrder, rows, conflict_cols=["pack_barcode"])
    db.commit()

    rtn_code, msg = rtn_for_judgments()
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)


@router.get("/work-order/batches/{batch_number}/summary", response_model=StandardResponse)
def get_batch_summary(
    batch_number: str,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access(STATION)),
):
    summary = compute_batch_summary(db, batch_number)
    if summary is None:
        raise MESError(RTN.REFERENCE_NOT_FOUND, f"No work order data recorded for batch '{batch_number}'")
    return StandardResponse(rtnCode=RTN.SUCCESS, msg="OK", data=summary)


@router.get("/work-order/orders/{work_order_id}/summary", response_model=StandardResponse)
def get_work_order_summary(
    work_order_id: str,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access(STATION)),
):
    """Rolls up every batch sharing this work_order_id — a work order can be
    split across multiple batch_numbers in production."""
    summary = compute_work_order_summary(db, work_order_id)
    if summary is None:
        raise MESError(RTN.REFERENCE_NOT_FOUND, f"No work order data recorded for work_order_id '{work_order_id}'")
    return StandardResponse(rtnCode=RTN.SUCCESS, msg="OK", data=summary)
