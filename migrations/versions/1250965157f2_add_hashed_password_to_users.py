
"""Add hashed password to users

Revision ID: 1250965157f2
Revises: 930d6ac8e3b5
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "1250965157f2"
down_revision: Union[str, Sequence[str], None] = "930d6ac8e3b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "hashed_password")
