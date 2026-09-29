"""Add Google identity association to marketplace accounts."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8a21c70d9e31"
down_revision: Union[str, Sequence[str], None] = "667fc21ce439"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_subject", sa.String(length=255), nullable=True))
    op.create_index("ix_users_google_subject", "users", ["google_subject"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_google_subject", table_name="users")
    op.drop_column("users", "google_subject")
