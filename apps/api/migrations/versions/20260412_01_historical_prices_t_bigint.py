"""Upgrade historical_prices.t from Integer to BigInteger.

Revision ID: 20260412_01
Revises:
Create Date: 2026-04-12 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "20260412_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "historical_prices" not in inspector.get_table_names():
        return

    col = next((c for c in inspector.get_columns("historical_prices") if c["name"] == "t"), None)
    if col is None:
        return

    if isinstance(col["type"], sa.BigInteger):
        return

    # Use an explicit cast to keep existing epoch values during type change.
    op.alter_column(
        "historical_prices",
        "t",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        postgresql_using="t::bigint",
        existing_nullable=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "historical_prices" not in inspector.get_table_names():
        return

    col = next((c for c in inspector.get_columns("historical_prices") if c["name"] == "t"), None)
    if col is None:
        return

    if isinstance(col["type"], sa.Integer):
        return

    max_bigint = bind.execute(sa.text("SELECT MAX(t) FROM historical_prices")).scalar()
    if max_bigint is not None and int(max_bigint) > 2147483647:
        raise RuntimeError("Cannot downgrade historical_prices.t to Integer: value exceeds 32-bit range")

    op.alter_column(
        "historical_prices",
        "t",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        postgresql_using="t::integer",
        existing_nullable=False,
    )
