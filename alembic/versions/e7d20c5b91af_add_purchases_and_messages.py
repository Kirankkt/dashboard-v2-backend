"""add purchases and messages

Revision ID: e7d20c5b91af
Revises: c4a91e02d7b5
Create Date: 2026-07-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7d20c5b91af'
down_revision: Union[str, Sequence[str], None] = 'c4a91e02d7b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    purchase_status = sa.Enum(
        'to_order', 'ordered', 'in_transit', 'delivered', 'cancelled', name='purchasestatus'
    )
    purchase_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'purchases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('item', sa.String(), nullable=False),
        sa.Column('supplier', sa.String(), nullable=False),
        sa.Column('cost', sa.Float(), nullable=False),
        sa.Column('order_date', sa.Date(), nullable=True),
        sa.Column('expected_date', sa.Date(), nullable=True),
        sa.Column('arrival_date', sa.Date(), nullable=True),
        sa.Column('status', purchase_status, nullable=False, server_default='to_order'),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('purchases', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_purchases_project_id'), ['project_id'], unique=False)

    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('body', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_messages_project_id'), ['project_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_messages_project_id'))
    op.drop_table('messages')
    with op.batch_alter_table('purchases', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_purchases_project_id'))
    op.drop_table('purchases')
    sa.Enum(name='purchasestatus').drop(op.get_bind(), checkfirst=True)
