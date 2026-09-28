"""add_user_id_to_creators_and_brands

Revision ID: 5eb83efae818
Revises: 05cff6633ec2
Create Date: 2026-09-28 21:34:01.189520

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5eb83efae818'
down_revision: Union[str, Sequence[str], None] = '05cff6633ec2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('brands', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_unique_constraint('uq_brands_user_id', 'brands', ['user_id'])
    op.create_foreign_key('fk_brands_user_id', 'brands', 'users', ['user_id'], ['user_id'], ondelete='SET NULL')
    op.add_column('creators', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_unique_constraint('uq_creators_user_id', 'creators', ['user_id'])
    op.create_foreign_key('fk_creators_user_id', 'creators', 'users', ['user_id'], ['user_id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_creators_user_id', 'creators', type_='foreignkey')
    op.drop_constraint('uq_creators_user_id', 'creators', type_='unique')
    op.drop_column('creators', 'user_id')
    op.drop_constraint('fk_brands_user_id', 'brands', type_='foreignkey')
    op.drop_constraint('uq_brands_user_id', 'brands', type_='unique')
    op.drop_column('brands', 'user_id')
