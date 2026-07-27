import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin

"""Master identity tables for cross-station traceability.

A row here means "this code has been seen and is legitimate" — it is
created as a side effect of the station that first introduces the
identity (cell-sorting for cells, cell-module-binding for modules,
module-pack-binding for packs), and checked by every downstream station
that references the code. See app/services/genealogy.py.
"""


class Cell(Base, TimestampMixin):
    __tablename__ = "cells"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cell_code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    proline_code: Mapped[str] = mapped_column(String(120), nullable=False)
    first_station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    # Latest cell-sorting judgment. A cell must be OK here before it can be
    # bound into a module — see ensure_cells_sorted_ok in genealogy.py.
    pass_information: Mapped[str] = mapped_column(String(8), nullable=False)


class Module(Base, TimestampMixin):
    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mod_code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    proline_code: Mapped[str] = mapped_column(String(120), nullable=False)
    first_station_code: Mapped[str] = mapped_column(String(120), nullable=False)
    # Set by module-eol-test (null until then). A module must be OK here
    # before it can be bound into a pack — see ensure_modules_passed_eol.
    eol_pass_information: Mapped[str | None] = mapped_column(String(8), nullable=True)


class Pack(Base, TimestampMixin):
    __tablename__ = "packs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pack_code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    proline_code: Mapped[str] = mapped_column(String(120), nullable=False)
    first_station_code: Mapped[str] = mapped_column(String(120), nullable=False)


class Operator(Base, TimestampMixin):
    """Traceability-only master table — auto-registered from `usercode` on
    every station submission (all 11 endpoints except Auto Stacking, which
    has no operator field). Never blocks ingestion and requires no
    pre-provisioning; see app/services/operators.py."""

    __tablename__ = "operators"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operator_code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    operator_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    first_station_code: Mapped[str] = mapped_column(String(120), nullable=False)
