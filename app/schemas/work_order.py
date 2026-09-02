from pydantic import Field

from app.schemas.common import CodeStr, MESBaseModel, MesTimestamp, ProductionDataRequest, WorkOrderStatusStr


class WorkOrderRecord(MESBaseModel):
    # A work_order_id can span multiple batch_numbers (production splits one
    # work order across several batches) — batch_number remains the upsert/
    # dedup key (one row per pack_barcode), work_order_id is the grouping
    # field one level up. See app/services/work_order_summary.py.
    work_order_id: CodeStr
    product_name: CodeStr
    series_configuration: CodeStr
    parallel_configuration: CodeStr
    category: CodeStr
    quantity: int = Field(ge=1)
    batch_number: CodeStr
    pack_barcode: CodeStr
    current_status: WorkOrderStatusStr
    actual_time: MesTimestamp | None = None
    completion_time: MesTimestamp | None = None


class WorkOrderRequest(ProductionDataRequest[WorkOrderRecord]):
    pass


class WorkOrderSummary(MESBaseModel):
    """Good/rejected yield for a batch or a whole work order (one or more
    batches), computed live from cell- and pack-level pass_information —
    see app/services/work_order_summary.py."""

    target_quantity: int
    reported_quantity: int
    completed_quantity: int
    pending_quantity: int
    good_quantity: int
    rejected_quantity: int
    batch_number: str | None = None
    work_order_id: str | None = None
    batch_count: int | None = None
