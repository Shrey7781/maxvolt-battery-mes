import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class WorkOrder(Base, TimestampMixin):
    """One row per pack barcode within a vendor-pushed work order/batch,
    manually entered at one or two station devices (not yet decided which).

    Deliberately independent of the cell/module/pack genealogy tables in
    app/models/entities.py: a work order can be pushed before, after, or
    without any corresponding module-pack-binding row ever landing, so
    pack_barcode carries no FK to packs.pack_code and no genealogy gate
    runs against it (see app/routers/work_order.py)."""

    __tablename__ = "work_orders"
    __table_args__ = (UniqueConstraint("pack_barcode", name="uq_work_order_pack_barcode"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    # One work_order_id can span multiple batch_numbers — see the module
    # docstring in app/services/work_order_summary.py.
    work_order_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(120), nullable=False)
    series_configuration: Mapped[str] = mapped_column(String(120), nullable=False)
    parallel_configuration: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    batch_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    pack_barcode: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    current_status: Mapped[str] = mapped_column(String(120), nullable=False)
    actual_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    completion_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
