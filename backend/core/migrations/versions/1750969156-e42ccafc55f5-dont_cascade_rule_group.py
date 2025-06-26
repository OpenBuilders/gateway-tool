"""dont cascade rule group

Revision ID: e42ccafc55f5
Revises: ec82e8aa0d67
Create Date: 2025-06-26 20:19:16.827965

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e42ccafc55f5"
down_revision: Union[str, None] = "ec82e8aa0d67"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "telegram_chat_emoji_group_id_fkey", "telegram_chat_emoji", type_="foreignkey"
    )
    op.create_foreign_key(
        None,
        "telegram_chat_emoji",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="NO ACTION",
    )
    op.drop_constraint(
        "telegram_chat_gift_collection_group_id_fkey",
        "telegram_chat_gift_collection",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_gift_collection",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="NO ACTION",
    )
    op.drop_constraint(
        "telegram_chat_jetton_group_id_fkey", "telegram_chat_jetton", type_="foreignkey"
    )
    op.create_foreign_key(
        None,
        "telegram_chat_jetton",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="NO ACTION",
    )
    op.drop_constraint(
        "telegram_chat_nft_collection_group_id_fkey",
        "telegram_chat_nft_collection",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_nft_collection",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="NO ACTION",
    )
    op.drop_constraint(
        "telegram_chat_premium_group_id_fkey",
        "telegram_chat_premium",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_premium",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="NO ACTION",
    )
    op.drop_constraint(
        "telegram_chat_sticker_collection_group_id_fkey",
        "telegram_chat_sticker_collection",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_sticker_collection",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="NO ACTION",
    )
    op.drop_constraint(
        "telegram_chat_toncoin_group_id_fkey",
        "telegram_chat_toncoin",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_toncoin",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="NO ACTION",
    )
    op.drop_constraint(
        "telegram_chat_whitelist_group_id_fkey",
        "telegram_chat_whitelist",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_whitelist",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="NO ACTION",
    )
    op.drop_constraint(
        "telegram_chat_whitelist_external_source_group_id_fkey",
        "telegram_chat_whitelist_external_source",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "telegram_chat_whitelist_external_source",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="NO ACTION",
    )


def downgrade() -> None:
    op.drop_constraint(
        None, "telegram_chat_whitelist_external_source", type_="foreignkey"
    )
    op.create_foreign_key(
        "telegram_chat_whitelist_external_source_group_id_fkey",
        "telegram_chat_whitelist_external_source",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(None, "telegram_chat_whitelist", type_="foreignkey")
    op.create_foreign_key(
        "telegram_chat_whitelist_group_id_fkey",
        "telegram_chat_whitelist",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(None, "telegram_chat_toncoin", type_="foreignkey")
    op.create_foreign_key(
        "telegram_chat_toncoin_group_id_fkey",
        "telegram_chat_toncoin",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(None, "telegram_chat_sticker_collection", type_="foreignkey")
    op.create_foreign_key(
        "telegram_chat_sticker_collection_group_id_fkey",
        "telegram_chat_sticker_collection",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(None, "telegram_chat_premium", type_="foreignkey")
    op.create_foreign_key(
        "telegram_chat_premium_group_id_fkey",
        "telegram_chat_premium",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(None, "telegram_chat_nft_collection", type_="foreignkey")
    op.create_foreign_key(
        "telegram_chat_nft_collection_group_id_fkey",
        "telegram_chat_nft_collection",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(None, "telegram_chat_jetton", type_="foreignkey")
    op.create_foreign_key(
        "telegram_chat_jetton_group_id_fkey",
        "telegram_chat_jetton",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(None, "telegram_chat_gift_collection", type_="foreignkey")
    op.create_foreign_key(
        "telegram_chat_gift_collection_group_id_fkey",
        "telegram_chat_gift_collection",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(None, "telegram_chat_emoji", type_="foreignkey")
    op.create_foreign_key(
        "telegram_chat_emoji_group_id_fkey",
        "telegram_chat_emoji",
        "telegram_chat_rule_group",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
