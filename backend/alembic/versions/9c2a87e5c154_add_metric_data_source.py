"""Track metric source for API attribution and retention."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c2a87e5c154"
down_revision: Union[str, Sequence[str], None] = "5eb83efae818"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "creator_metrics",
        sa.Column("data_source", sa.String(length=30), server_default="manual", nullable=False),
    )
    op.create_index(
        "ix_creator_metrics_source_date",
        "creator_metrics",
        ["data_source", "metric_date"],
    )
    op.add_column(
        "creator_metrics",
        sa.Column("total_videos", sa.BigInteger(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("creator_metrics", "total_videos")
    op.drop_index("ix_creator_metrics_source_date", table_name="creator_metrics")
    op.drop_column("creator_metrics", "data_source")
