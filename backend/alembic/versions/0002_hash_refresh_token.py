"""hash refresh token column

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop unique index before altering column type/size
    op.drop_index("ix_refresh_tokens_token", table_name="refresh_tokens")

    # Truncate existing plain-text tokens — they can no longer be validated
    # after switching to sha256 storage, so clearing them forces re-login.
    op.execute("DELETE FROM refresh_tokens")

    op.alter_column(
        "refresh_tokens",
        "token",
        existing_type=sa.String(length=512),
        type_=sa.String(length=64),
        existing_nullable=False,
    )

    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_token", table_name="refresh_tokens")
    op.execute("DELETE FROM refresh_tokens")
    op.alter_column(
        "refresh_tokens",
        "token",
        existing_type=sa.String(length=64),
        type_=sa.String(length=512),
        existing_nullable=False,
    )
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"], unique=True)
