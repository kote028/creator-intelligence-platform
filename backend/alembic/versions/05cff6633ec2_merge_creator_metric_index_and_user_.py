"""Merge creator metric index and user migrations

Revision ID: 05cff6633ec2
Revises: 872d82715b75, 2f0455afadd2
Create Date: 2026-09-02 15:53:41.214413

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05cff6633ec2'
down_revision: Union[str, Sequence[str], None] = ('872d82715b75', '2f0455afadd2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
