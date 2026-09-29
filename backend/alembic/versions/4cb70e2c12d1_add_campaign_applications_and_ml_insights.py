"""Add campaign applications and sponsorship initiation metadata."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4cb70e2c12d1"
down_revision: Union[str, Sequence[str], None] = "9c2a87e5c154"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sponsorships",
        sa.Column("initiated_by", sa.String(length=20), server_default="brand", nullable=False),
    )
    op.add_column(
        "sponsorships",
        sa.Column("application_message", sa.String(length=2000), nullable=True),
    )
    op.create_index(
        "ix_sponsorships_status_initiator",
        "sponsorships",
        ["status", "initiated_by"],
    )


def downgrade() -> None:
    op.drop_index("ix_sponsorships_status_initiator", table_name="sponsorships")
    op.drop_column("sponsorships", "application_message")
    op.drop_column("sponsorships", "initiated_by")
