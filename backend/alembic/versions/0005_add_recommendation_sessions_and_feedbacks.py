"""add recommendation_sessions and feedbacks

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recommendation_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("user_valence", sa.Float(), nullable=False),
        sa.Column("user_energy", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_recommendation_sessions_user_id", "recommendation_sessions", ["user_id"])

    op.create_table(
        "feedbacks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("track_id", sa.String(), sa.ForeignKey("music_catalog.track_id"), nullable=False),
        sa.Column("recommendation_id", sa.String(36), sa.ForeignKey("recommendation_sessions.id"), nullable=False),
        sa.Column("feedback_type", sa.Enum("like", "dislike", name="feedbacktype"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_feedbacks_user_id", "feedbacks", ["user_id"])
    op.create_unique_constraint(
        "uq_feedback_user_track_session", "feedbacks", ["user_id", "track_id", "recommendation_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_feedback_user_track_session", "feedbacks", type_="unique")
    op.drop_index("ix_feedbacks_user_id", "feedbacks")
    op.drop_table("feedbacks")
    op.execute("DROP TYPE IF EXISTS feedbacktype")
    op.drop_index("ix_recommendation_sessions_user_id", "recommendation_sessions")
    op.drop_table("recommendation_sessions")
