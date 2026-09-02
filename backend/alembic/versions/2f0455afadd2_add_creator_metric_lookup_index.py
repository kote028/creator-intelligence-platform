"""Add creator metric lookup index

Revision ID: 2f0455afadd2
Revises: eb8e79b5a1bf
Create Date: 2026-09-02
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2f0455afadd2"
down_revision: Union[str, Sequence[str], None] = "eb8e79b5a1bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_creator_metrics_account_date_id",
        "creator_metrics",
        [
            "account_id",
            "metric_date",
            "metric_id",
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_creator_metrics_account_date_id",
        table_name="creator_metrics",
    )
