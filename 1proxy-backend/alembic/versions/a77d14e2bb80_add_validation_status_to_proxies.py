"""add_validation_status_to_proxies

Revision ID: a77d14e2bb80
Revises: 98867adc7088
Create Date: 2026-01-12 22:11:46.259374

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a77d14e2bb80"
down_revision: Union[str, None] = "98867adc7088"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "proxies",
        sa.Column(
            "validation_status", sa.String(20), nullable=False, server_default="pending"
        ),
    )
    op.create_index("ix_proxies_validation_status", "proxies", ["validation_status"])


def downgrade() -> None:
    op.drop_index("ix_proxies_validation_status", table_name="proxies")
    op.drop_column("proxies", "validation_status")
