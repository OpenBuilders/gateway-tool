import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Integer,
    ForeignKey,
    BigInteger,
    String,
    Boolean,
    DateTime,
    func,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import mapped_column, relationship, Mapped

from core.db import Base

if TYPE_CHECKING:
    from core.models.gift import GiftCollection


class TelegramChatPremium(Base):
    __tablename__ = "telegram_chat_premium"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id = mapped_column(
        ForeignKey("telegram_chat.id", ondelete="CASCADE"), nullable=False
    )
    is_enabled = mapped_column(Boolean, nullable=False, default=False)
    created_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    __table_args__ = (
        UniqueConstraint("chat_id", name="uix_chat_premium_chat_id_unique"),
    )


class TelegramChatEmoji(Base):
    __tablename__ = "telegram_chat_emoji"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id = mapped_column(
        ForeignKey("telegram_chat.id", ondelete="CASCADE"),
        nullable=False,
    )
    emoji_id = mapped_column(String(255), nullable=False)
    logo_url = mapped_column(String(255), nullable=True)
    is_enabled = mapped_column(Boolean, nullable=False, default=False)
    created_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    __table_args__ = (
        UniqueConstraint("chat_id", name="uix_chat_emoji_chat_id_unique"),
    )


class TelegramChatRuleBase(Base):
    __abstract__ = True

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id = mapped_column(
        ForeignKey("telegram_chat.id", ondelete="CASCADE"), nullable=False
    )
    threshold = mapped_column(
        BigInteger, nullable=False, doc="Minimum amount of items to hold"
    )
    category = mapped_column(
        String(255),
        nullable=True,
        doc="Optional category name that is mapped to the logic in the code",
    )
    grants_write_access = mapped_column(Boolean, nullable=False, default=False)
    is_enabled = mapped_column(Boolean, nullable=False, default=True)
    created_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TelegramChatToncoin(TelegramChatRuleBase):
    __tablename__ = "telegram_chat_toncoin"


class TelegramChatJetton(TelegramChatRuleBase):
    __tablename__ = "telegram_chat_jetton"

    address = mapped_column(
        ForeignKey("jetton.address", ondelete="CASCADE"), nullable=False
    )
    jetton = relationship(
        "Jetton",
        back_populates="telegram_chat_jettons",
        lazy="joined",
    )

    def __repr__(self):
        return f"<TelegramChatJetton({self.address=}, {self.chat_id=})>"


class TelegramChatNFTCollection(TelegramChatRuleBase):
    __tablename__ = "telegram_chat_nft_collection"

    address = mapped_column(
        ForeignKey("nft_collection.address", ondelete="CASCADE"), nullable=True
    )

    asset = mapped_column(
        String(255),
        nullable=True,
        doc="Asset type that will be used to check eligibility for the collection",
    )

    nft_collection = relationship(
        "NFTCollection",
        back_populates="telegram_chat_nft_collections",
        lazy="joined",
    )

    def __repr__(self):
        return f"<TelegramChatNFTCollection({self.address=}, {self.chat_id=})>"


class TelegramChatWhitelistBase(Base):
    __abstract__ = True

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id = mapped_column(
        ForeignKey("telegram_chat.id", ondelete="CASCADE"), nullable=False
    )
    name = mapped_column(String(255), nullable=False)
    description = mapped_column(String(255), nullable=True)
    is_enabled = mapped_column(Boolean, nullable=False, default=True)
    content = mapped_column(
        JSON,
        nullable=True,
        doc="List of Telegram IDs as integers that are allowed to access the chat, e.g. `[123455, 122234, 123456]`",
    )
    created_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=datetime.datetime.now,
        nullable=False,
    )


class TelegramChatWhitelistExternalSource(TelegramChatWhitelistBase):
    __tablename__ = "telegram_chat_whitelist_external_source"

    url = mapped_column(String(2000), nullable=False)
    auth_key = mapped_column(
        String(255),
        nullable=True,
        doc="Header name that will be used for authentication",
    )
    auth_value = mapped_column(
        String(255),
        nullable=True,
        doc="Header value that will be used for authentication",
    )

    __table_args__ = (
        UniqueConstraint(
            "chat_id", "name", name="uix_chat_external_source_chat_name_unique"
        ),
    )

    def __repr__(self):
        return f"<TelegramChatWhitelistExternalSource({self.url=}, {self.chat_id=})>"


class TelegramChatWhitelist(TelegramChatWhitelistBase):
    __tablename__ = "telegram_chat_whitelist"

    def __repr__(self):
        return f"<TelegramChatWhitelist({self.chat_id=}, {self.name=})>"

    __table_args__ = (
        UniqueConstraint("chat_id", "name", name="uix_chat_whitelist_chat_name_unique"),
    )


class TelegramChatStickerCollection(TelegramChatRuleBase):
    __tablename__ = "telegram_chat_sticker_collection"
    collection_id = mapped_column(
        ForeignKey("sticker_collection.id", ondelete="CASCADE"),
        nullable=True,
        doc="Collection ID that will be used to check eligibility for the collection.",
    )
    collection = relationship(
        "StickerCollection",
        lazy="joined",
        viewonly=True,
    )
    character_id = mapped_column(
        ForeignKey("sticker_character.id", ondelete="CASCADE"),
        nullable=True,
        doc="Character ID that will be used to check eligibility for the collection.",
    )
    character = relationship(
        "StickerCharacter",
        lazy="joined",
        viewonly=True,
    )


class TelegramChatGiftCollection(TelegramChatRuleBase):
    __tablename__ = "telegram_chat_gift_collection"
    collection_slug = mapped_column(
        ForeignKey("gift_collection.slug", ondelete="CASCADE"),
        nullable=True,
        doc="Collection slug that will be used to check eligibility for the collection.",
    )
    collection: Mapped["GiftCollection"] = relationship(
        "GiftCollection",
        lazy="joined",
        viewonly=True,
    )
    model = mapped_column(
        String(255),
        nullable=True,
        doc="Model that will be used to check eligibility for the collection.",
    )
    backdrop = mapped_column(
        String(255),
        nullable=True,
        doc="Backdrop that will be used to check eligibility for the collection.",
    )
    pattern = mapped_column(
        String(255),
        nullable=True,
        doc="Pattern that will be used to check eligibility for the collection.",
    )
