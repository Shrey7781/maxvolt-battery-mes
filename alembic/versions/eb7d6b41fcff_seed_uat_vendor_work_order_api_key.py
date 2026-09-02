"""seed UAT vendor work-order api key

Revision ID: eb7d6b41fcff
Revises: aa729e7de9da
Create Date: 2026-09-02 03:27:12.732743

Seeds one API key for the work-order station slug, same pattern as
f3a1c9d4b7e2 seeded one per original vendor station. device_name is
deliberately generic ("UAT Vendor - work-order") rather than naming a
specific physical station, since which physical device(s) will actually
post to this endpoint isn't decided yet (see mes-backend/CLAUDE.md /
../CLAUDE.md) -- the key is scoped to the work-order slug only, same
isolation model as every other key, and works for whichever device ends up
holding it.

Only the SHA-256 hash is stored here, same as the app always stores
(app/security.py hash_api_key) -- the raw value was generated locally,
shown once, and is not recoverable from this file or the database.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'eb7d6b41fcff'
down_revision: Union[str, None] = 'aa729e7de9da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


api_keys_table = sa.table(
    'api_keys',
    sa.column('id', postgresql.UUID(as_uuid=True)),
    sa.column('device_name', sa.String),
    sa.column('key_hash', sa.String),
    sa.column('allowed_stations', postgresql.ARRAY(sa.String)),
    sa.column('is_active', sa.Boolean),
)

KEY_ID = "4364e69d-81b6-49e1-b9d3-6f0726b1269e"
KEY_HASH = "be137018449c1b742762f5e7ae96d0f56fd117a1eaf479365360291af7019b56"


def upgrade() -> None:
    op.bulk_insert(
        api_keys_table,
        [
            {
                "id": KEY_ID,
                "device_name": "UAT Vendor - work-order",
                "key_hash": KEY_HASH,
                "allowed_stations": ["work-order"],
                "is_active": True,
            }
        ],
    )


def downgrade() -> None:
    op.execute(api_keys_table.delete().where(api_keys_table.c.id == KEY_ID))
