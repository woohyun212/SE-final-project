"""add music_catalog table

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "music_catalog",
        sa.Column("track_id", sa.String(64), primary_key=True),
        sa.Column("track_name", sa.String(512), nullable=False),
        sa.Column("artists", sa.Text(), nullable=False),
        sa.Column("album_name", sa.String(512), nullable=False),
        sa.Column("track_genre", sa.String(128), nullable=False),
        sa.Column("popularity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("preview_url", sa.String(512), nullable=True),
        sa.Column("danceability", sa.Float(), nullable=False),
        sa.Column("energy", sa.Float(), nullable=False),
        sa.Column("valence", sa.Float(), nullable=False),
        sa.Column("acousticness", sa.Float(), nullable=False),
        sa.Column("instrumentalness", sa.Float(), nullable=False),
        sa.Column("speechiness", sa.Float(), nullable=False),
        sa.Column("liveness", sa.Float(), nullable=False),
        sa.Column("tempo", sa.Float(), nullable=False),
        sa.Column("loudness", sa.Float(), nullable=False),
        sa.Column("key", sa.Integer(), nullable=False),
        sa.Column("mode", sa.Integer(), nullable=False),
        sa.Column("time_signature", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("music_catalog")
