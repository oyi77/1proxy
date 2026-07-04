"""add_can_access_openai_to_proxies

Revision ID: 5f8a3c1d2e4b
Revises: 412f1c5bb27a
Create Date: 2025-07-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f8a3c1d2e4b'
down_revision: Union[str, None] = '412f1c5bb27a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('proxies') as batch_op:
        batch_op.add_column(sa.Column('can_access_openai', sa.Boolean(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('proxies') as batch_op:
        batch_op.drop_column('can_access_openai')