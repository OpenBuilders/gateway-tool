"""

Revision ID: c3cbfd0a74d2
Revises: 
Create Date: 2025-05-15 14:33:48.632864

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import JSON
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "c3cbfd0a74d2"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "jetton",
        sa.Column("address", sa.String(length=67), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", mysql.TEXT(), nullable=True),
        sa.Column("symbol", sa.String(length=255), nullable=False),
        sa.Column("total_supply", sa.BigInteger(), nullable=False),
        sa.Column("logo_path", sa.String(length=290), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("address"),
    )
    op.create_table(
        "nft_collection",
        sa.Column("address", sa.String(length=67), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", mysql.TEXT(), nullable=True),
        sa.Column("logo_path", sa.String(length=290), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("blockchain_metadata", JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("address"),
    )
    op.create_table(
        "sticker_collection",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("logo_url", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "telegram_chat",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("is_forum", sa.Boolean(), nullable=False),
        sa.Column("logo_path", sa.String(length=55), nullable=True),
        sa.Column("invite_link", sa.String(length=255), nullable=True),
        sa.Column("insufficient_privileges", sa.Boolean(), nullable=False),
        sa.Column("is_full_control", sa.Boolean(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("is_premium", sa.Boolean(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("is_blocked", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("allows_write_to_pm", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_telegram_id"), "user", ["telegram_id"], unique=True)
    op.create_index(op.f("ix_user_username"), "user", ["username"], unique=False)
    op.create_table(
        "sticker_character",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("supply", sa.Integer(), nullable=False),
        sa.Column("logo_url", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["sticker_collection.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "external_id",
            "collection_id",
            name="uq_character_external_id_collection_id",
        ),
    )
    op.create_index(
        op.f("ix_sticker_character_external_id"),
        "sticker_character",
        ["external_id"],
        unique=False,
    )
    op.create_table(
        "telegram_chat_emoji",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("emoji_id", sa.String(length=255), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["telegram_chat.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id", name="uix_chat_emoji_chat_id_unique"),
    )
    op.create_table(
        "telegram_chat_jetton",
        sa.Column("address", sa.String(length=67), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("threshold", sa.BigInteger(), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("grants_write_access", sa.Boolean(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["address"], ["jetton.address"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chat_id"], ["telegram_chat.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "telegram_chat_nft_collection",
        sa.Column("address", sa.String(length=67), nullable=True),
        sa.Column("asset", sa.String(length=255), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("threshold", sa.BigInteger(), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("grants_write_access", sa.Boolean(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["address"], ["nft_collection.address"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["telegram_chat.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "telegram_chat_premium",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["telegram_chat.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id", name="uix_chat_premium_chat_id_unique"),
    )
    op.create_table(
        "telegram_chat_toncoin",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("threshold", sa.BigInteger(), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("grants_write_access", sa.Boolean(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["telegram_chat.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "telegram_chat_user",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("is_managed", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["telegram_chat.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "chat_id"),
    )
    op.create_table(
        "telegram_chat_whitelist",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("content", mysql.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["telegram_chat.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "chat_id", "name", name="uix_chat_whitelist_chat_name_unique"
        ),
    )
    op.create_table(
        "telegram_chat_whitelist_external_source",
        sa.Column("url", sa.String(length=255), nullable=False),
        sa.Column("auth_key", sa.String(length=255), nullable=True),
        sa.Column("auth_value", sa.String(length=255), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("content", mysql.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["telegram_chat.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "chat_id", "name", name="uix_chat_external_source_chat_name_unique"
        ),
    )
    op.create_table(
        "user_wallet",
        sa.Column("address", sa.String(length=67), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("balance", mysql.BIGINT(), nullable=True),
        sa.Column("hide_wallet", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("address"),
        sa.UniqueConstraint("address", "user_id", name="uq_wallet_address_user_id"),
    )
    op.create_table(
        "jetton_wallet",
        sa.Column("address", sa.String(length=67), nullable=False),
        sa.Column("jetton_master_address", sa.String(length=67), nullable=False),
        sa.Column("owner_address", sa.String(length=67), nullable=False),
        sa.Column("balance", mysql.BIGINT(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["jetton_master_address"], ["jetton.address"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["owner_address"], ["user_wallet.address"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("address"),
    )
    op.create_table(
        "nft_item",
        sa.Column("address", sa.String(length=67), nullable=False),
        sa.Column("owner_address", sa.String(length=67), nullable=False),
        sa.Column("collection_address", sa.String(length=67), nullable=False),
        sa.Column("blockchain_metadata", JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["collection_address"], ["nft_collection.address"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["owner_address"], ["user_wallet.address"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("address"),
    )
    op.create_table(
        "sticker_item",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=True),
        sa.Column("instance", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"], ["sticker_character.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["sticker_collection.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "telegram_chat_sticker_collection",
        sa.Column("collection_id", sa.Integer(), nullable=True),
        sa.Column("character_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("threshold", sa.BigInteger(), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("grants_write_access", sa.Boolean(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["character_id"], ["sticker_character.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["telegram_chat.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["sticker_collection.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "telegram_chat_user_wallet",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("address", sa.String(length=67), nullable=False),
        sa.ForeignKeyConstraint(
            ["address"], ["user_wallet.address"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["telegram_chat.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("chat_id", "address"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("telegram_chat_user_wallet")
    op.drop_table("telegram_chat_sticker_collection")
    op.drop_table("sticker_item")
    op.drop_table("nft_item")
    op.drop_table("jetton_wallet")
    op.drop_table("user_wallet")
    op.drop_table("telegram_chat_whitelist_external_source")
    op.drop_table("telegram_chat_whitelist")
    op.drop_table("telegram_chat_user")
    op.drop_table("telegram_chat_toncoin")
    op.drop_table("telegram_chat_premium")
    op.drop_table("telegram_chat_nft_collection")
    op.drop_table("telegram_chat_jetton")
    op.drop_table("telegram_chat_emoji")
    op.drop_index(
        op.f("ix_sticker_character_external_id"), table_name="sticker_character"
    )
    op.drop_table("sticker_character")
    op.drop_index(op.f("ix_user_username"), table_name="user")
    op.drop_index(op.f("ix_user_telegram_id"), table_name="user")
    op.drop_table("user")
    op.drop_table("telegram_chat")
    op.drop_table("sticker_collection")
    op.drop_table("nft_collection")
    op.drop_table("jetton")
    # ### end Alembic commands ###
