"""Add campaign advertising fields and sponsorship outcome reports."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "667fc21ce439"
down_revision: Union[str, Sequence[str], None] = "4cb70e2c12d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("advertising_field", sa.String(length=100), nullable=True))
    op.create_table(
        "campaign_results",
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("sponsorship_id", sa.Integer(), nullable=False),
        sa.Column("impressions", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("conversions", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("attributed_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("reported_at", sa.Date(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["sponsorship_id"], ["sponsorships.sponsorship_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("result_id"),
        sa.UniqueConstraint("sponsorship_id", name="uq_campaign_results_sponsorship"),
    )
    op.create_index("ix_campaign_results_reported_at", "campaign_results", ["reported_at"])


def downgrade() -> None:
    op.drop_index("ix_campaign_results_reported_at", table_name="campaign_results")
    op.drop_table("campaign_results")
    op.drop_column("campaigns", "advertising_field")
