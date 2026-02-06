"""Add analytics models

Revision ID: b565ec5cefb1
Revises: 26c76ca321fe
Create Date: 2026-02-02 22:13:58.408917

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b565ec5cefb1"
down_revision: Union[str, None] = "26c76ca321fe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop and recreate analytics tables if they exist
    # This prevents DuplicateTable errors when migration runs multiple times
    old_tables = ["usage_logs", "source_trust_scores", "proxy_performance_history"]

    # Drop tables safely (they may not exist, which is fine)
    for table in old_tables:
        try:
            op.drop_table(table, if_exists=True)
        except Exception:
            pass

    # Drop indexes on proxies if they exist
    try:
        op.drop_index(
            op.f("ix_proxies_source_id"), table_name="proxies", if_exists=True
        )
    except Exception:
        pass

    # Create usage_logs table
    op.create_table(
        "usage_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for usage_logs
    op.create_index(
        op.f("ix_usage_logs_created_at"), "usage_logs", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_usage_logs_id"), "usage_logs", ["id"], unique=False)
    op.create_index(
        op.f("ix_usage_logs_user_id"), "usage_logs", ["user_id"], unique=False
    )

    # Create source_trust_scores table
    op.create_table(
        "source_trust_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("trust_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["proxy_sources.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for source_trust_scores
    op.create_index(
        op.f("ix_source_trust_scores_id"), "source_trust_scores", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_source_trust_scores_source_id"),
        "source_trust_scores",
        ["source_id"],
        unique=False,
    )

    # Create proxy_performance_history table
    op.create_table(
        "proxy_performance_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("proxy_id", sa.Integer(), nullable=False),
        sa.Column(
            "validated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("latency_p50", sa.Float(), nullable=True),
        sa.Column("latency_p95", sa.Float(), nullable=True),
        sa.Column("uptime_percent", sa.Float(), nullable=True),
        sa.Column("packet_loss", sa.Float(), nullable=True),
        sa.Column("jitter_ms", sa.Float(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["proxy_id"], ["proxies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for proxy_performance_history
    op.create_index(
        op.f("ix_proxy_performance_history_id"),
        "proxy_performance_history",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_proxy_performance_history_proxy_id"),
        "proxy_performance_history",
        ["proxy_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_proxy_performance_history_validated_at"),
        "proxy_performance_history",
        ["validated_at"],
        unique=False,
    )


def downgrade() -> None:
    # Drop all analytics tables and indexes
    old_tables = ["usage_logs", "source_trust_scores", "proxy_performance_history"]

    for table in old_tables:
        try:
            op.drop_table(table, if_exists=True)
        except Exception:
            pass

    try:
        op.drop_index(
            op.f("ix_proxies_source_id"), table_name="proxies", if_exists=True
        )
    except Exception:
        pass
