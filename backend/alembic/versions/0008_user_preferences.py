"""add user_preferences

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-04

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("like_danceability", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("like_energy", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("like_valence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("like_acousticness", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("like_instrumentalness", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dislike_danceability", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("dislike_energy", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("dislike_valence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("dislike_acousticness", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("dislike_instrumentalness", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("dislike_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
