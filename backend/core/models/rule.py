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


class TelegramChatRuleGroup(Base):
    __tablename__ = "telegram_chat_rule_group"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_chat.id", ondelete="CASCADE"), nullable=False
    )
    chat = relationship(
        "TelegramChat",
        backref="rule_groups",
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TelegramChatRuleBase(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_chat_rule_group.id", ondelete="CASCADE"), nullable=False
    )
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_chat.id", ondelete="CASCADE"), nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    grants_write_access: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TelegramChatPremium(TelegramChatRuleBase):
    __tablename__ = "telegram_chat_premium"

    __table_args__ = (
        UniqueConstraint("chat_id", name="uix_chat_premium_chat_id_unique"),
    )


class TelegramChatEmoji(TelegramChatRuleBase):
    __tablename__ = "telegram_chat_emoji"

    emoji_id = mapped_column(String(255), nullable=False)
    __table_args__ = (
        UniqueConstraint("chat_id", name="uix_chat_emoji_chat_id_unique"),
    )


class TelegramChatThresholdRuleBase(TelegramChatRuleBase):
    __abstract__ = True

    threshold = mapped_column(
        BigInteger, nullable=False, doc="Minimum amount of items to hold"
    )
    category = mapped_column(
        String(255),
        nullable=True,
        doc="Optional category name that is mapped to the logic in the code",
    )


class TelegramChatToncoin(TelegramChatThresholdRuleBase):
    __tablename__ = "telegram_chat_toncoin"


class TelegramChatJetton(TelegramChatThresholdRuleBase):
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


class TelegramChatNFTCollection(TelegramChatThresholdRuleBase):
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


class TelegramChatWhitelistBase(TelegramChatRuleBase):
    __abstract__ = True

    name = mapped_column(String(255), nullable=False)
    description = mapped_column(String(255), nullable=True)
    content = mapped_column(
        JSON,
        nullable=True,
        doc="List of Telegram IDs as integers that are allowed to access the chat, e.g. `[123455, 122234, 123456]`",
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


class TelegramChatStickerCollection(TelegramChatThresholdRuleBase):
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
    group = relationship(
        "TelegramChatRuleGroup",
        backref="sticker_collection_rules",
    )
    chat = relationship(
        "TelegramChat",
        backref="sticker_collection_rules",
    )
    character = relationship(
        "StickerCharacter",
        lazy="joined",
        viewonly=True,
    )


class TelegramChatGiftCollection(TelegramChatThresholdRuleBase):
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
