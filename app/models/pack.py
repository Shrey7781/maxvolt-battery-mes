import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class ModulePackBinding(Base, TimestampMixin):
    __tablename__ = "module_pack_bindings"
    __table_args__ = (
        UniqueConstraint("mod_code", name="uq_module_pack_binding_module"),
        UniqueConstraint("pack_code", "mod_index", name="uq_module_pack_binding_pack_slot"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    proline_code: Mapped[str] = mapped_column(String(120), nullable=False)
    mod_code: Mapped[str] = mapped_column(String(120), ForeignKey("modules.mod_code"), nullable=False, index=True)
    pack_code: Mapped[str] = mapped_column(String(120), ForeignKey("packs.pack_code"), nullable=False, index=True)
    mod_index: Mapped[int] = mapped_column(Integer, nullable=False)
    bms_code: Mapped[str] = mapped_column(String(120), nullable=False)
    station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    usercode: Mapped[str] = mapped_column(
        String(120), ForeignKey("operators.operator_code"), nullable=False, index=True
    )
    employee_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class LiquidCoolingAirtightnessReading(Base, TimestampMixin):
    __tablename__ = "liquid_cooling_airtightness_readings"
    __table_args__ = (UniqueConstraint("pack_code", name="uq_liquid_cooling_pack"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    proline_code: Mapped[str] = mapped_column(String(120), nullable=False)
    pack_code: Mapped[str] = mapped_column(String(120), ForeignKey("packs.pack_code"), nullable=False, index=True)
    cooled_code: Mapped[str] = mapped_column(String(120), nullable=False)
    chargetime: Mapped[float] = mapped_column(Float, nullable=False)
    holdtime: Mapped[float] = mapped_column(Float, nullable=False)
    testtime: Mapped[float] = mapped_column(Float, nullable=False)
    pressure: Mapped[float] = mapped_column(Float, nullable=False)
    leakage: Mapped[float] = mapped_column(Float, nullable=False)
    result: Mapped[str] = mapped_column(String(8), nullable=False)
    station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    usercode: Mapped[str] = mapped_column(
        String(120), ForeignKey("operators.operator_code"), nullable=False, index=True
    )
    employee_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class PackEolTestReading(Base, TimestampMixin):
    __tablename__ = "pack_eol_test_readings"
    __table_args__ = (UniqueConstraint("pack_code", name="uq_pack_eol_pack"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    pack_code: Mapped[str] = mapped_column(String(120), ForeignKey("packs.pack_code"), nullable=False, index=True)
    test_file_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    pass_information: Mapped[str] = mapped_column(String(8), nullable=False)
    usercode: Mapped[str] = mapped_column(
        String(120), ForeignKey("operators.operator_code"), nullable=False, index=True
    )
    employee_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class PackAirtightnessReading(Base, TimestampMixin):
    __tablename__ = "pack_airtightness_readings"
    __table_args__ = (UniqueConstraint("pack_code", name="uq_pack_airtightness_pack"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    proline_code: Mapped[str] = mapped_column(String(120), nullable=False)
    pack_code: Mapped[str] = mapped_column(String(120), ForeignKey("packs.pack_code"), nullable=False, index=True)
    chargetime: Mapped[float] = mapped_column(Float, nullable=False)
    holdtime: Mapped[float] = mapped_column(Float, nullable=False)
    testtime: Mapped[float] = mapped_column(Float, nullable=False)
    pressure: Mapped[float] = mapped_column(Float, nullable=False)
    leakage: Mapped[float] = mapped_column(Float, nullable=False)
    result: Mapped[str] = mapped_column(String(8), nullable=False)
    station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    usercode: Mapped[str] = mapped_column(
        String(120), ForeignKey("operators.operator_code"), nullable=False, index=True
    )
    employee_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
