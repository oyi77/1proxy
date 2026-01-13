"""add_composite_index_for_query_optimization

Revision ID: 92afc781690f
Revises: a77d14e2bb80
Create Date: 2026-01-13 13:01:07.438918

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "92afc781690f"
down_revision: Union[str, None] = "a77d14e2bb80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add composite index for optimizing the most common query pattern:
    # WHERE is_working = true AND validation_status = 'validated' ORDER BY quality_score DESC
    op.create_index(
        "idx_proxy_working_status_quality",
        "proxies",
        ["is_working", "validation_status", "quality_score"],
        unique=False,
    )


def downgrade() -> None:
    # Remove the composite index
    op.drop_index("idx_proxy_working_status_quality", table_name="proxies")
