"""manual_add_isp_org

Revision ID: 26c76ca321fe
Revises: 9f610160ba2b
Create Date: 2026-02-02 16:52:27.239595

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26c76ca321fe'
down_revision: Union[str, None] = '9f610160ba2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
