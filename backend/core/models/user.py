from sqlalchemy import Integer, String, DateTime, Boolean, BigInteger, func
from sqlalchemy.orm import mapped_column, relationship

from core.db import Base
from core.settings import core_settings


class User(Base):
    __tablename__ = "user"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id = mapped_column(BigInteger, unique=True, index=True)
    is_premium = mapped_column(Boolean, default=False, nullable=False)
    username = mapped_column(String(255), index=True, nullable=True)
    first_name = mapped_column(String(255), nullable=False)
    last_name = mapped_column(String(255), nullable=True)
    language = mapped_column(
        String(10), nullable=False, default=core_settings.default_language
    )
    is_blocked = mapped_column(Boolean, nullable=False, default=False)
    is_admin = mapped_column(Boolean, nullable=False, default=False)

    created_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    allows_write_to_pm = mapped_column(Boolean, nullable=False, default=True)

    wallets = relationship(
        "UserWallet",
        uselist=True,
        backref="user",
        lazy="joined",
        primaryjoin="User.id == UserWallet.user_id",
    )
    wallet_links = relationship(
        "TelegramChatUserWallet",
        uselist=True,
        back_populates="user",
    )

    @property
    def full_name(self) -> str:
        return " ".join(filter(lambda x: x, [self.first_name, self.last_name]))

    def __repr__(self) -> str:
        return f"<User {self.id=!r} {self.username=!r}>"
