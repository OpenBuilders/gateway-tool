from sqlalchemy import (
    BigInteger,
    String,
    DateTime,
    func,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import mapped_column, relationship

from core.db import Base


class TelegramChat(Base):
    __tablename__ = "telegram_chat"

    id = mapped_column(BigInteger, primary_key=True)
    username = mapped_column(String(255), nullable=True)
    title = mapped_column(String(255), nullable=False)
    description = mapped_column(String(255), nullable=True)
    slug = mapped_column(String(255), nullable=False, unique=True)
    is_forum = mapped_column(Boolean, nullable=False, default=False)
    logo_path = mapped_column(String(55), nullable=True)
    invite_link = mapped_column(
        String(255),
        nullable=True,
        doc="Invite link to the chat. If empty, the chat will not be accessible.",
    )
    insufficient_privileges = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether the chat has insufficient privileges to be managed by the bot.",
    )
    is_full_control = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc=(
            "Whether the bot should fully control the chat,"
            " e.g. joined outside of the current invite link, previously joined."
        ),
    )
    is_enabled = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether the chat should be managed by the bot and available for users..",
    )
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TelegramChat(id={self.id}, title={self.title})>"


class TelegramChatUser(Base):
    __tablename__ = "telegram_chat_user"

    user_id = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    chat_id = mapped_column(
        ForeignKey("telegram_chat.id", ondelete="CASCADE"), primary_key=True
    )
    is_admin = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether the user is an admin in the chat",
    )
    is_managed = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="If user is managed by bot, meaning that join request was approved by bot and should be if eligibility status changed, etc.",
    )
    created_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", lazy="joined", overlaps="wallet_link")
    chat = relationship("TelegramChat", lazy="joined", backref="users")
    wallet_link = relationship(
        "TelegramChatUserWallet",
        uselist=False,
        back_populates="user_chat",
        primaryjoin="and_(foreign(TelegramChatUser.user_id) == TelegramChatUserWallet.user_id, foreign(TelegramChatUser.chat_id) == TelegramChatUserWallet.chat_id)",
        lazy="joined",
        viewonly=True,
    )

    def __repr__(self):
        return f"<TelegramChatUser(user_id={self.user_id}, chat_id={self.chat_id})>"
