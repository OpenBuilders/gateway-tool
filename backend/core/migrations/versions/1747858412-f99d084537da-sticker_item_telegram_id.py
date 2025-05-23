"""sticker item telegram id

Revision ID: f99d084537da
Revises: c3cbfd0a74d2
Create Date: 2025-05-21 20:13:32.367969

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f99d084537da"
down_revision: Union[str, None] = "c3cbfd0a74d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # It was added in the pre-release phase, and it'll be easier to reindex data after the migration is done
    op.execute(sa.text("DELETE FROM sticker_item WHERE true"))
    op.add_column(
        "sticker_item", sa.Column("telegram_user_id", sa.BigInteger(), nullable=False)
    )
    op.create_index(
        op.f("ix_sticker_item_telegram_user_id"),
        "sticker_item",
        ["telegram_user_id"],
        unique=False,
    )
    op.drop_constraint("sticker_item_user_id_fkey", "sticker_item", type_="foreignkey")
    op.drop_column("sticker_item", "user_id")


def downgrade() -> None:
    op.add_column(
        "sticker_item",
        sa.Column("user_id", sa.INTEGER(), autoincrement=False, nullable=False),
    )
    op.create_foreign_key(
        "sticker_item_user_id_fkey",
        "sticker_item",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_index(op.f("ix_sticker_item_telegram_user_id"), table_name="sticker_item")
    op.drop_column("sticker_item", "telegram_user_id")
