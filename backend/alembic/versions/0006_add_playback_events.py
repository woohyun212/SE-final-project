"""add playback_events

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-30

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "playback_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("track_id", sa.String(), sa.ForeignKey("music_catalog.track_id"), nullable=False),
        sa.Column("event", sa.String(16), nullable=False),
        sa.Column("playback_pct", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_playback_events_user_id", "playback_events", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_playback_events_user_id", "playback_events")
    op.drop_table("playback_events")
