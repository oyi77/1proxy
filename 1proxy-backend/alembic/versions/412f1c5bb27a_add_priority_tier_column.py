"""add_priority_tier_column

Revision ID: 412f1c5bb27a
Revises: 39dc06e4ef90
Create Date: 2026-05-04 23:57:25.460097

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '412f1c5bb27a'
down_revision: Union[str, None] = '39dc06e4ef90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('proxies') as batch_op:
        batch_op.add_column(sa.Column('priority_tier', sa.Integer(), nullable=True))

    # Update existing rows with priority tier values
    op.execute("""
        UPDATE proxies SET priority_tier = CASE
            WHEN quality_score >= 80 AND anonymity = 'elite' THEN 1
            WHEN quality_score >= 60 AND anonymity IN ('elite', 'anonymous') THEN 2
            WHEN validation_status = 'validated' AND is_working = TRUE THEN 3
            ELSE 4
        END
    """)

    # Use batch_alter_table to set NOT NULL constraint
    with op.batch_alter_table('proxies') as batch_op:
        batch_op.alter_column('priority_tier', nullable=False)

    op.create_index('idx_proxy_tier_validated', 'proxies', ['priority_tier', 'last_validated'], unique=False)
    op.create_index(op.f('ix_proxies_priority_tier'), 'proxies', ['priority_tier'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_proxies_priority_tier'), table_name='proxies')
    op.drop_index('idx_proxy_tier_validated', table_name='proxies')
    with op.batch_alter_table('proxies') as batch_op:
        batch_op.drop_column('priority_tier')