"""telegram chat rule group

Revision ID: ec82e8aa0d67
Revises: 53b283880538
Create Date: 2025-06-19 15:08:10.234943

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ec82e8aa0d67"
down_revision: Union[str, None] = "53b283880538"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def create_rule_group_table() -> None:
    op.create_table(
        "telegram_chat_rule_group",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["telegram_chat.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def create_rule_group_columns() -> None:
    """
    Create new columns with 0 as the default value to avoid raising a null constraint error.
    The actual value will be set in the migration script.
    """
    op.add_column(
        "telegram_chat_emoji",
        sa.Column("group_id", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "telegram_chat_emoji",
        sa.Column(
            "grants_write_access", sa.Boolean(), nullable=False, server_default="true"
        ),
    )
    op.add_column(
        "telegram_chat_gift_collection",
        sa.Column("group_id", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "telegram_chat_jetton",
        sa.Column("group_id", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "telegram_chat_nft_collection",
        sa.Column("group_id", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "telegram_chat_premium",
        sa.Column("group_id", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "telegram_chat_premium",
        sa.Column(
            "grants_write_access", sa.Boolean(), nullable=False, server_default="true"
        ),
    )
    op.add_column(
        "telegram_chat_sticker_collection",
        sa.Column("group_id", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "telegram_chat_toncoin",
        sa.Column("group_id", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "telegram_chat_whitelist",
        sa.Column("group_id", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "telegram_chat_whitelist",
        sa.Column(
            "grants_write_access", sa.Boolean(), nullable=False, server_default="true"
        ),
    )
    op.add_column(
        "telegram_chat_whitelist_external_source",
        sa.Column("group_id", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "telegram_chat_whitelist_external_source",
        sa.Column(
            "grants_write_access", sa.Boolean(), nullable=False, server_default="true"
        ),
    )


def create_rule_group_records() -> dict[int, int]:
    # Create default rule groups for all `telegram_chat` entities
    connection = op.get_bind()

    # Get all telegram chat IDs
    telegram_chats = (
        connection.execute(sa.text("SELECT id FROM telegram_chat")).scalars().fetchall()
    )

    # Create mapping dictionary
    chat_group_mapping = {}

    # Create rule groups for each chat
    for chat in telegram_chats:
        result = connection.execute(
            sa.text(
                'INSERT INTO telegram_chat_rule_group (chat_id, "order") VALUES (:chat_id, :order) RETURNING id'
            ),
            {"chat_id": chat, "order": 1},
        )
        group_id = result.scalar()
        chat_group_mapping[chat] = group_id

    return chat_group_mapping


def set_proper_rule_group_id_in_table(
    rule_table_name: str, chat_id_group_id_mapping: dict[int, int]
) -> None:
    connection = op.get_bind()
    # Convert the mapping to a list of dictionaries
    params = [
        {"chat_id": chat_id, "group_id": group_id}
        for chat_id, group_id in chat_id_group_id_mapping.items()
    ]

    # Use executemany for better performance with many records
    connection.execute(
        sa.text(
            f"UPDATE {rule_table_name} SET group_id = :group_id WHERE chat_id = :chat_id"
        ),
        params,
    )


def set_proper_rule_group_id(chat_id_group_id_mapping: dict[int, int]) -> None:
    for table_name in [
        "telegram_chat_emoji",
        "telegram_chat_gift_collection",
        "telegram_chat_jetton",
        "telegram_chat_nft_collection",
        "telegram_chat_premium",
        "telegram_chat_sticker_collection",
        "telegram_chat_toncoin",
        "telegram_chat_whitelist",
        "telegram_chat_whitelist_external_source",
    ]:
        set_proper_rule_group_id_in_table(table_name, chat_id_group_id_mapping)


def create_foreign_keys() -> None:
    op.create_foreign_key(
        None,
        "telegram_chat_emoji",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_gift_collection",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_jetton",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_nft_collection",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_premium",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_sticker_collection",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_toncoin",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_whitelist",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_whitelist_external_source",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )


def upgrade() -> None:
    create_rule_group_table()
    create_rule_group_columns()
    mapping = create_rule_group_records()
    set_proper_rule_group_id(mapping)
    create_foreign_keys()


def downgrade() -> None:
    op.drop_constraint(
        "telegram_chat_whitelist_external_source_group_id_fkey",
        "telegram_chat_whitelist_external_source",
        type_="foreignkey",
    )
    op.drop_column("telegram_chat_whitelist_external_source", "grants_write_access")
    op.drop_column("telegram_chat_whitelist_external_source", "group_id")
    op.drop_constraint(
        "telegram_chat_whitelist_group_id_fkey",
        "telegram_chat_whitelist",
        type_="foreignkey",
    )
    op.drop_column("telegram_chat_whitelist", "grants_write_access")
    op.drop_column("telegram_chat_whitelist", "group_id")
    op.drop_constraint(
        "telegram_chat_toncoin_group_id_fkey",
        "telegram_chat_toncoin",
        type_="foreignkey",
    )
    op.drop_column("telegram_chat_toncoin", "group_id")
    op.drop_constraint(
        "telegram_chat_sticker_collection_group_id_fkey",
        "telegram_chat_sticker_collection",
        type_="foreignkey",
    )
    op.drop_column("telegram_chat_sticker_collection", "group_id")
    op.drop_constraint(
        "telegram_chat_premium_group_id_fkey",
        "telegram_chat_premium",
        type_="foreignkey",
    )
    op.drop_column("telegram_chat_premium", "grants_write_access")
    op.drop_column("telegram_chat_premium", "group_id")
    op.drop_constraint(
        "telegram_chat_nft_collection_group_id_fkey",
        "telegram_chat_nft_collection",
        type_="foreignkey",
    )
    op.drop_column("telegram_chat_nft_collection", "group_id")
    op.drop_constraint(
        "telegram_chat_jetton_group_id_fkey", "telegram_chat_jetton", type_="foreignkey"
    )
    op.drop_column("telegram_chat_jetton", "group_id")
    op.drop_constraint(
        "telegram_chat_gift_collection_group_id_fkey",
        "telegram_chat_gift_collection",
        type_="foreignkey",
    )
    op.drop_column("telegram_chat_gift_collection", "group_id")
    op.drop_constraint(
        "telegram_chat_emoji_group_id_fkey", "telegram_chat_emoji", type_="foreignkey"
    )
    op.drop_column("telegram_chat_emoji", "grants_write_access")
    op.drop_column("telegram_chat_emoji", "group_id")
    op.drop_table("telegram_chat_rule_group")
