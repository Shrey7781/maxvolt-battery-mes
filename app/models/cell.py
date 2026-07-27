import uuid

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class CellSortingReading(Base, TimestampMixin):
    __tablename__ = "cell_sorting_readings"
    __table_args__ = (UniqueConstraint("cell_code", "station_code", name="uq_cell_sorting_cell_station"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    proline_code: Mapped[str] = mapped_column(String(120), nullable=False)
    cell_code: Mapped[str] = mapped_column(String(120), ForeignKey("cells.cell_code"), nullable=False, index=True)
    station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    voltage: Mapped[float] = mapped_column(Float, nullable=False)
    inter_res: Mapped[float] = mapped_column(Float, nullable=False)
    nnr: Mapped[float] = mapped_column(Float, nullable=False)
    pass_information: Mapped[str] = mapped_column(String(8), nullable=False)
    usercode: Mapped[str] = mapped_column(
        String(120), ForeignKey("operators.operator_code"), nullable=False, index=True
    )
    employee_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
