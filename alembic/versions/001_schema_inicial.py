"""Schema inicial: tenants, products, stock_movements, stock_lots, sales, expenses.

Revision ID: 001
Revises:
Create Date: 2026-05-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  # Banco novo: create_all via init_db é suficiente.
  # Esta revision documenta o schema congelado para PostgreSQL futuro.
  pass


def downgrade() -> None:
    pass
