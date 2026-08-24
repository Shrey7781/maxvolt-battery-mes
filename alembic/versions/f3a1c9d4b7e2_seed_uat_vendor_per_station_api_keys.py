"""seed UAT vendor per-station api keys

Revision ID: f3a1c9d4b7e2
Revises: 6ec7512308d9
Create Date: 2026-08-24 12:00:00.000000

Seeds one API key per station for the Chinese vendor's UAT commissioning,
each scoped to exactly one station slug (not "*") so a compromised or
misconfigured device on one station can't post as another -- same isolation
model as every other key provisioned via scripts/manage_api_keys.py.

Only the SHA-256 hash of each raw key is stored here, same as the app
always stores (app/security.py hash_api_key) -- the raw values were
generated locally, shown once to the operator provisioning this migration,
and are not recoverable from this file or the database.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f3a1c9d4b7e2'
down_revision: Union[str, None] = '6ec7512308d9'
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

SEED_KEYS = [
    {
        "id": "8b7ded2b-e231-40da-ac5c-68951e0e8c7d",
        "device_name": "UAT Vendor - cell-sorting",
        "key_hash": "127d190ecf4b38f49664e120d5ac071e06466338cf300ffbee290dd769890687",
        "station": "cell-sorting",
    },
    {
        "id": "740ed048-5afc-49cb-ae18-60eadd4b642b",
        "device_name": "UAT Vendor - cell-module-binding",
        "key_hash": "b06e5ff6af57f7f6336f9f69798db31a68711474ddbb6954f862fd17e9ae9441",
        "station": "cell-module-binding",
    },
    {
        "id": "9aa66be1-312a-4a0a-80a9-913baa687e10",
        "device_name": "UAT Vendor - auto-stacking",
        "key_hash": "90e226132b821ab22cc0eb4355a05bc4190948792add0cf316e8b1d4ae6f879e",
        "station": "auto-stacking",
    },
    {
        "id": "4912d7e3-4b24-4ab3-88ec-3ed91bc0616e",
        "device_name": "UAT Vendor - polarity-detection",
        "key_hash": "493d4f6afe5672c50f3c3d725229eb4536e69d3423e15c030f13d9f6e623c430",
        "station": "polarity-detection",
    },
    {
        "id": "960f8540-bb92-4c1e-9fd9-2637f231fe3f",
        "device_name": "UAT Vendor - laser-cleaning",
        "key_hash": "a47c29e4a06cc2dc2bcf10fefba2c54ef8b8beb6594961940a8b94e016914dcb",
        "station": "laser-cleaning",
    },
    {
        "id": "ed482b67-0677-44d8-9427-594cd9810a4d",
        "device_name": "UAT Vendor - laser-welding",
        "key_hash": "b18b618100d2e4eb72580253db9a12045c5d919e55c8c08474e504c6a677a697",
        "station": "laser-welding",
    },
    {
        "id": "ab54547c-b973-4d72-9bf1-277c68ce963b",
        "device_name": "UAT Vendor - module-eol-test",
        "key_hash": "92ccc1ef7817ecafd25581096400ffd7ed4f5ce1f7b35de8d69795a13b4c0f07",
        "station": "module-eol-test",
    },
    {
        "id": "92d71335-78ba-4730-b6ba-28b6b21ecc51",
        "device_name": "UAT Vendor - module-pack-binding",
        "key_hash": "14647e9f6aebd0804147db8d438679ad586e49fe3ba90636c5ef9b6f8adb4ee8",
        "station": "module-pack-binding",
    },
    {
        "id": "5eaa9f00-2e0e-42f8-9293-4e14c6e319b6",
        "device_name": "UAT Vendor - liquid-cooling-airtightness",
        "key_hash": "ffc196c4f72b7951bf90cdbd5e7e021922c917990144634f77d52a4ef07173cd",
        "station": "liquid-cooling-airtightness",
    },
    {
        "id": "c04b6626-3165-4639-8dbe-555429f09260",
        "device_name": "UAT Vendor - pack-eol-test",
        "key_hash": "2560c0fdf9ac56bc14b385d3d370aa33badd965c940450b008ee35fdc0c0bf3c",
        "station": "pack-eol-test",
    },
    {
        "id": "6abd1c11-ac8d-487c-88eb-0e0d355ccbde",
        "device_name": "UAT Vendor - pack-airtightness",
        "key_hash": "ecac45a13cf4b58a0bd71f46396d97a0db50fabe29dd453b5ea568f8d682aba0",
        "station": "pack-airtightness",
    },
]


def upgrade() -> None:
    op.bulk_insert(
        api_keys_table,
        [
            {
                "id": row["id"],
                "device_name": row["device_name"],
                "key_hash": row["key_hash"],
                "allowed_stations": [row["station"]],
                "is_active": True,
            }
            for row in SEED_KEYS
        ],
    )


def downgrade() -> None:
    ids = [row["id"] for row in SEED_KEYS]
    op.execute(
        api_keys_table.delete().where(api_keys_table.c.id.in_(ids))
    )
