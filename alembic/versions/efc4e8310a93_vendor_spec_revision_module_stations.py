"""vendor spec revision: module station field changes

Revision ID: efc4e8310a93
Revises: eb7d6b41fcff
Create Date: 2026-10-27 12:00:00.000000

Schema side of the vendor's 2026-10 interface spec revision
(uat_vendor_api_spec(revised).xlsx, yellow-highlighted changes):

  - polarity-detection: col_coord has no practical length limit (the
    vision system emits the module's whole terminal-coordinate list, up to
    ~10000 chars) -> Text.
  - laser-welding: cell_coord likewise -> Text; usercode removed from the
    payload -> column made nullable (kept, not dropped, so rows recorded
    before the change keep their operator ID).
  - laser-cleaning: cell_coord replaced by mark_info (mark point
    coordinates) -> column renamed, natural key now (mod_code, mark_info).
    Values already stored under cell_coord carry over into mark_info as-is.

A long Text value can't sit in a btree index entry (~2.7KB cap), so the two
coordinate natural keys move from plain unique constraints to unique
indexes on (mod_code, md5(coord)) — same uniqueness semantics, bounded
index size. Same names are reused so nothing else needs to know.

The remaining revision changes (station order: liquid-cooling-airtightness
now creates the pack, module-pack-binding requires it; leakage may be
negative) are application-level only and need no schema change.

Downgrade intentionally fails rather than truncating if any coordinate
longer than 120 chars or any laser-welding row with a null usercode has
been recorded since.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'efc4e8310a93'
down_revision: Union[str, None] = 'eb7d6b41fcff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('uq_polarity_module_coord', 'polarity_detection_readings', type_='unique')
    op.alter_column(
        'polarity_detection_readings', 'col_coord',
        type_=sa.Text(), existing_type=sa.String(length=120), existing_nullable=False,
    )
    op.create_index(
        'uq_polarity_module_coord', 'polarity_detection_readings',
        ['mod_code', sa.text('md5(col_coord)')], unique=True,
    )

    op.drop_constraint('uq_laser_cleaning_module_coord', 'laser_cleaning_readings', type_='unique')
    op.alter_column(
        'laser_cleaning_readings', 'cell_coord',
        new_column_name='mark_info', existing_type=sa.String(length=120), existing_nullable=False,
    )
    op.create_unique_constraint('uq_laser_cleaning_module_mark', 'laser_cleaning_readings', ['mod_code', 'mark_info'])

    op.drop_constraint('uq_laser_welding_module_coord', 'laser_welding_readings', type_='unique')
    op.alter_column(
        'laser_welding_readings', 'cell_coord',
        type_=sa.Text(), existing_type=sa.String(length=120), existing_nullable=False,
    )
    op.create_index(
        'uq_laser_welding_module_coord', 'laser_welding_readings',
        ['mod_code', sa.text('md5(cell_coord)')], unique=True,
    )
    op.alter_column(
        'laser_welding_readings', 'usercode',
        existing_type=sa.String(length=120), nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'laser_welding_readings', 'usercode',
        existing_type=sa.String(length=120), nullable=False,
    )
    op.drop_index('uq_laser_welding_module_coord', table_name='laser_welding_readings')
    op.alter_column(
        'laser_welding_readings', 'cell_coord',
        type_=sa.String(length=120), existing_type=sa.Text(), existing_nullable=False,
    )
    op.create_unique_constraint('uq_laser_welding_module_coord', 'laser_welding_readings', ['mod_code', 'cell_coord'])

    op.drop_constraint('uq_laser_cleaning_module_mark', 'laser_cleaning_readings', type_='unique')
    op.alter_column(
        'laser_cleaning_readings', 'mark_info',
        new_column_name='cell_coord', existing_type=sa.String(length=120), existing_nullable=False,
    )
    op.create_unique_constraint('uq_laser_cleaning_module_coord', 'laser_cleaning_readings', ['mod_code', 'cell_coord'])

    op.drop_index('uq_polarity_module_coord', table_name='polarity_detection_readings')
    op.alter_column(
        'polarity_detection_readings', 'col_coord',
        type_=sa.String(length=120), existing_type=sa.Text(), existing_nullable=False,
    )
    op.create_unique_constraint('uq_polarity_module_coord', 'polarity_detection_readings', ['mod_code', 'col_coord'])
