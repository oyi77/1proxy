"""add isp and org columns to proxies

Revision ID: 39dc06e4ef90
Revises: b565ec5cefb1
Create Date: 2026-02-06 04:00:38.872040

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "39dc06e4ef90"
down_revision: Union[str, None] = "b565ec5cefb1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_columns = {col["name"] for col in inspector.get_columns("proxies")}

    with op.batch_alter_table("proxies") as batch_op:
        if "isp" not in existing_columns:
            batch_op.add_column(sa.Column("isp", sa.String(length=200), nullable=True))
        if "org" not in existing_columns:
            batch_op.add_column(sa.Column("org", sa.String(length=200), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_columns = {col["name"] for col in inspector.get_columns("proxies")}

    with op.batch_alter_table("proxies") as batch_op:
        if "org" in existing_columns:
            batch_op.drop_column("org")
        if "isp" in existing_columns:
            batch_op.drop_column("isp")
