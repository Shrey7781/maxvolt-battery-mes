import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin

# Polarity col_coord and laser-welding cell_coord are vision-system coordinate
# lists that can run to thousands of characters — too long to sit in a btree
# index directly (Postgres caps an index entry at ~2.7KB, so a long value
# would fail the insert). Their (mod_code, coord) natural keys are therefore
# enforced by a unique index on md5(coord) instead of the raw text; the
# routers pass the matching expression as the upsert's ON CONFLICT target
# (see app/routers/module.py).


class CellModuleBinding(Base, TimestampMixin):
    __tablename__ = "cell_module_bindings"
    __table_args__ = (UniqueConstraint("cell_code", name="uq_cell_module_binding_cell"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    proline_code: Mapped[str] = mapped_column(String(120), nullable=False)
    mod_code: Mapped[str] = mapped_column(String(120), ForeignKey("modules.mod_code"), nullable=False, index=True)
    cell_code: Mapped[str] = mapped_column(String(120), ForeignKey("cells.cell_code"), nullable=False)
    cell_index: Mapped[int] = mapped_column(Integer, nullable=False)
    station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    usercode: Mapped[str] = mapped_column(
        String(120), ForeignKey("operators.operator_code"), nullable=False, index=True
    )
    employee_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class AutoStackingReading(Base, TimestampMixin):
    __tablename__ = "auto_stacking_readings"
    __table_args__ = (UniqueConstraint("mod_code", name="uq_auto_stacking_module"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    proline_code: Mapped[str] = mapped_column(String(120), nullable=False)
    mod_code: Mapped[str] = mapped_column(String(120), ForeignKey("modules.mod_code"), nullable=False, index=True)
    start_pressure: Mapped[float] = mapped_column(Float, nullable=False)
    end_pressure: Mapped[float] = mapped_column(Float, nullable=False)
    average_pressure: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class PolarityDetectionReading(Base, TimestampMixin):
    __tablename__ = "polarity_detection_readings"
    __table_args__ = (Index("uq_polarity_module_coord", "mod_code", text("md5(col_coord)"), unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    mod_code: Mapped[str] = mapped_column(String(120), ForeignKey("modules.mod_code"), nullable=False, index=True)
    col_coord: Mapped[str] = mapped_column(Text, nullable=False)
    mark_info: Mapped[str] = mapped_column(String(255), nullable=False)
    pass_information: Mapped[str] = mapped_column(String(8), nullable=False)
    usercode: Mapped[str] = mapped_column(
        String(120), ForeignKey("operators.operator_code"), nullable=False, index=True
    )
    employee_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class LaserCleaningReading(Base, TimestampMixin):
    __tablename__ = "laser_cleaning_readings"
    __table_args__ = (UniqueConstraint("mod_code", "mark_info", name="uq_laser_cleaning_module_mark"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    mod_code: Mapped[str] = mapped_column(String(120), ForeignKey("modules.mod_code"), nullable=False, index=True)
    mark_info: Mapped[str] = mapped_column(String(120), nullable=False)
    cleaning_power: Mapped[float] = mapped_column(Float, nullable=False)
    speed: Mapped[float] = mapped_column(Float, nullable=False)
    pass_information: Mapped[str] = mapped_column(String(8), nullable=False)
    usercode: Mapped[str] = mapped_column(
        String(120), ForeignKey("operators.operator_code"), nullable=False, index=True
    )
    employee_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class LaserWeldingReading(Base, TimestampMixin):
    __tablename__ = "laser_welding_readings"
    __table_args__ = (Index("uq_laser_welding_module_coord", "mod_code", text("md5(cell_coord)"), unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    mod_code: Mapped[str] = mapped_column(String(120), ForeignKey("modules.mod_code"), nullable=False, index=True)
    cell_coord: Mapped[str] = mapped_column(Text, nullable=False)
    welding_power: Mapped[float] = mapped_column(Float, nullable=False)
    speed: Mapped[float] = mapped_column(Float, nullable=False)
    pass_information: Mapped[str] = mapped_column(String(8), nullable=False)
    # The vendor's 2026-10 spec revision dropped usercode from this station.
    # Kept as a nullable column (rather than dropped) so readings recorded
    # before the change keep their operator ID; new rows leave it null.
    usercode: Mapped[str | None] = mapped_column(
        String(120), ForeignKey("operators.operator_code"), nullable=True, index=True
    )
    employee_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class ModuleEolTestReading(Base, TimestampMixin):
    __tablename__ = "module_eol_test_readings"
    __table_args__ = (UniqueConstraint("mod_code", name="uq_module_eol_module"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    mod_code: Mapped[str] = mapped_column(String(120), ForeignKey("modules.mod_code"), nullable=False, index=True)
    mod_V: Mapped[float] = mapped_column(Float, nullable=False)
    mod_V_Result: Mapped[str] = mapped_column(String(8), nullable=False)
    mod_R: Mapped[float] = mapped_column(Float, nullable=False)
    mod_R_Result: Mapped[str] = mapped_column(String(8), nullable=False)
    mod_IR: Mapped[float] = mapped_column(Float, nullable=False)
    mod_IR_Result: Mapped[str] = mapped_column(String(8), nullable=False)
    mod_DWV: Mapped[float] = mapped_column(Float, nullable=False)
    mod_DWV_Result: Mapped[str] = mapped_column(String(8), nullable=False)
    pass_information: Mapped[str] = mapped_column(String(8), nullable=False)
    usercode: Mapped[str] = mapped_column(
        String(120), ForeignKey("operators.operator_code"), nullable=False, index=True
    )
    employee_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
