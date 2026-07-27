import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class ApiKey(Base, TimestampMixin):
    """Credential for a single machine/device client.

    The raw key is only ever shown once, at creation time (see
    scripts/manage_api_keys.py). Only its SHA-256 hash is stored.
    """

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # List of station slugs (matching router paths, e.g. "cell-sorting") this
    # key may post to. "*" means all stations.
    allowed_stations: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
