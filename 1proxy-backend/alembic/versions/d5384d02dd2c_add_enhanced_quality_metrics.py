"""add_enhanced_quality_metrics

Revision ID: d5384d02dd2c
Revises: 5f8a3c1d2e4b
Create Date: 2026-07-08 05:56:23.856881

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5384d02dd2c'
down_revision: Union[str, None] = '5f8a3c1d2e4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get existing columns to avoid duplicate column errors
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {col['name'] for col in inspector.get_columns('proxies')}
    
    # Add new quality metric columns to proxies table - only if they don't exist
    with op.batch_alter_table('proxies', schema=None) as batch_op:
        if 'ssl_valid' not in existing_columns:
            batch_op.add_column(sa.Column('ssl_valid', sa.Boolean(), nullable=True))
        if 'anonymity_level' not in existing_columns:
            batch_op.add_column(sa.Column('anonymity_level', sa.String(20), nullable=True))
        if 'ip_blacklisted' not in existing_columns:
            batch_op.add_column(sa.Column('ip_blacklisted', sa.Boolean(), nullable=True))
        if 'dns_leak' not in existing_columns:
            batch_op.add_column(sa.Column('dns_leak', sa.Boolean(), nullable=True))
        if 'response_time_p95' not in existing_columns:
            batch_op.add_column(sa.Column('response_time_p95', sa.Integer(), nullable=True))
        if 'geolocation_verified' not in existing_columns:
            batch_op.add_column(sa.Column('geolocation_verified', sa.Boolean(), nullable=True))
        
    # Add indexes for quality metrics - only if they don't exist
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('proxies')}
    
    with op.batch_alter_table('proxies', schema=None) as batch_op:
        if 'ix_proxies_ssl_valid' not in existing_indexes:
            batch_op.create_index('ix_proxies_ssl_valid', ['ssl_valid'])
        if 'ix_proxies_anonymity_level' not in existing_indexes:
            batch_op.create_index('ix_proxies_anonymity_level', ['anonymity_level'])
        if 'ix_proxies_ip_blacklisted' not in existing_indexes:
            batch_op.create_index('ix_proxies_ip_blacklisted', ['ip_blacklisted'])
        if 'ix_proxies_geolocation_verified' not in existing_indexes:
            batch_op.create_index('ix_proxies_geolocation_verified', ['geolocation_verified'])

def downgrade() -> None:
    # Drop indexes first
    with op.batch_alter_table('proxies', schema=None) as batch_op:
        batch_op.drop_index('ix_proxies_can_access_openai')
        batch_op.drop_index('ix_proxies_can_access_google')
        batch_op.drop_index('ix_proxies_response_time')
        batch_op.drop_index('ix_proxies_anonymity_level')
        batch_op.drop_index('ix_proxies_last_validated')
        batch_op.drop_index('ix_proxies_validation_status')
        batch_op.drop_index('ix_proxies_quality_score')
    
    # Drop columns
    with op.batch_alter_table('proxies', schema=None) as batch_op:
        batch_op.drop_column('geolocation_verified')
        batch_op.drop_column('response_time_p95')
        batch_op.drop_column('dns_leak')
        batch_op.drop_column('ip_blacklisted')
        batch_op.drop_column('anonymity_level')
        batch_op.drop_column('ssl_valid')
