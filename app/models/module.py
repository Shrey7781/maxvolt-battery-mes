import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


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
    __table_args__ = (UniqueConstraint("mod_code", "col_coord", name="uq_polarity_module_coord"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    mod_code: Mapped[str] = mapped_column(String(120), ForeignKey("modules.mod_code"), nullable=False, index=True)
    col_coord: Mapped[str] = mapped_column(String(120), nullable=False)
    mark_info: Mapped[str] = mapped_column(String(255), nullable=False)
    pass_information: Mapped[str] = mapped_column(String(8), nullable=False)
    usercode: Mapped[str] = mapped_column(
        String(120), ForeignKey("operators.operator_code"), nullable=False, index=True
    )
    employee_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class LaserCleaningReading(Base, TimestampMixin):
    __tablename__ = "laser_cleaning_readings"
    __table_args__ = (UniqueConstraint("mod_code", "cell_coord", name="uq_laser_cleaning_module_coord"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    mod_code: Mapped[str] = mapped_column(String(120), ForeignKey("modules.mod_code"), nullable=False, index=True)
    cell_coord: Mapped[str] = mapped_column(String(120), nullable=False)
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
    __table_args__ = (UniqueConstraint("mod_code", "cell_coord", name="uq_laser_welding_module_coord"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    mod_code: Mapped[str] = mapped_column(String(120), ForeignKey("modules.mod_code"), nullable=False, index=True)
    cell_coord: Mapped[str] = mapped_column(String(120), nullable=False)
    welding_power: Mapped[float] = mapped_column(Float, nullable=False)
    speed: Mapped[float] = mapped_column(Float, nullable=False)
    pass_information: Mapped[str] = mapped_column(String(8), nullable=False)
    usercode: Mapped[str] = mapped_column(
        String(120), ForeignKey("operators.operator_code"), nullable=False, index=True
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
