"""add recommendation_results

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-03

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recommendation_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("recommendation_sessions.id"), nullable=False),
        sa.Column("track_id", sa.String(64), sa.ForeignKey("music_catalog.track_id"), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
    )
    op.create_index("ix_recommendation_results_session_id", "recommendation_results", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_recommendation_results_session_id", "recommendation_results")
    op.drop_table("recommendation_results")
