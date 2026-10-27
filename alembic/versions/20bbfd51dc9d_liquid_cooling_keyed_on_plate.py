"""liquid cooling airtightness keyed on the plate (cooled_code)

Revision ID: 20bbfd51dc9d
Revises: efc4e8310a93
Create Date: 2026-10-27 16:00:00.000000

Vendor clarification (2026-10-27) on station 08: on an NG result the device
still uploads the record with the liquid cooling plate barcode (cooled_code)
but no pack_code — pack_code is only generated when the plate passes. The
barcode is stuck on the plate and never replaced, so a retest of the same
plate sends the same cooled_code.

  - natural key moves from pack_code to cooled_code (new
    uq_liquid_cooling_plate).
  - pack_code becomes nullable (NG plates have none). It stays unique — one
    plate per pack — so uq_liquid_cooling_pack is kept as is; Postgres
    doesn't treat NULLs as equal, so it allows any number of NG rows.

Rows recorded before this change were keyed on pack_code, so the same
cooled_code can appear on more than one of them (e.g. UAT test posts reusing
an example barcode). The most recently updated row per cooled_code keeps it;
the older ones get a '#dup-<id>' suffix so the new unique constraint can be
created without deleting anything. Their original value is still in
raw_payload.

Downgrade intentionally fails rather than dropping data if any row has a
null pack_code.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20bbfd51dc9d'
down_revision: Union[str, None] = 'efc4e8310a93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    renamed = op.get_bind().execute(sa.text("""
        UPDATE liquid_cooling_airtightness_readings r
        SET cooled_code = left(r.cooled_code, 107) || '#dup-' || left(r.id::text, 8)
        FROM (
            SELECT id, row_number() OVER (
                PARTITION BY cooled_code ORDER BY updated_at DESC, created_at DESC, id
            ) AS rn
            FROM liquid_cooling_airtightness_readings
        ) ranked
        WHERE r.id = ranked.id AND ranked.rn > 1
    """)).rowcount
    if renamed:
        print(f"liquid_cooling_airtightness_readings: suffixed {renamed} older duplicate cooled_code value(s)")

    op.alter_column(
        'liquid_cooling_airtightness_readings', 'pack_code',
        existing_type=sa.String(length=120), nullable=True,
    )
    op.create_unique_constraint(
        'uq_liquid_cooling_plate', 'liquid_cooling_airtightness_readings', ['cooled_code'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_liquid_cooling_plate', 'liquid_cooling_airtightness_readings', type_='unique')
    op.alter_column(
        'liquid_cooling_airtightness_readings', 'pack_code',
        existing_type=sa.String(length=120), nullable=False,
    )
