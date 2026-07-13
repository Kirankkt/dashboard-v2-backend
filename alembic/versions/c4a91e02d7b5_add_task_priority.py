"""add task priority

Revision ID: c4a91e02d7b5
Revises: 8fcc31b5bc57
Create Date: 2026-07-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4a91e02d7b5'
down_revision: Union[str, Sequence[str], None] = '8fcc31b5bc57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    priority = sa.Enum('normal', 'high', name='taskpriority')
    priority.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'tasks',
        sa.Column('priority', priority, nullable=False, server_default='normal'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tasks', 'priority')
    sa.Enum(name='taskpriority').drop(op.get_bind(), checkfirst=True)
