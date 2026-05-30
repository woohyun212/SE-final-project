"""add auto-increment id to music_catalog for ML index mapping

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-27

"""
from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE music_catalog ADD COLUMN id SERIAL UNIQUE")
    op.create_index("ix_music_catalog_id", "music_catalog", ["id"])


def downgrade() -> None:
    op.drop_index("ix_music_catalog_id", "music_catalog")
    op.execute("ALTER TABLE music_catalog DROP COLUMN id")
