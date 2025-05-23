from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, BigInteger
from sqlalchemy.orm import mapped_column, relationship

from core.db import Base


class StickerCollection(Base):
    __tablename__ = "sticker_collection"

    id = mapped_column(Integer, primary_key=True)
    title = mapped_column(String(255), nullable=False)
    description = mapped_column(String(255), nullable=True)
    logo_url = mapped_column(String(255), nullable=True)


class StickerCharacter(Base):
    __tablename__ = "sticker_character"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id = mapped_column(Integer, nullable=False, index=True)
    collection_id = mapped_column(
        ForeignKey("sticker_collection.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = mapped_column(String(255), nullable=False)
    description = mapped_column(String(255), nullable=True)
    supply = mapped_column(Integer, nullable=False)
    logo_url = mapped_column(String(255), nullable=True)

    collection = relationship(
        "StickerCollection",
        backref="characters",
        lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint(
            "external_id",
            "collection_id",
            name="uq_character_external_id_collection_id",
        ),
    )


class StickerItem(Base):
    __tablename__ = "sticker_item"

    id = mapped_column(String(255), primary_key=True)
    collection_id = mapped_column(
        ForeignKey("sticker_collection.id", ondelete="CASCADE"),
        nullable=False,
    )
    character_id = mapped_column(
        ForeignKey("sticker_character.id", ondelete="CASCADE"),
    )
    instance = mapped_column(Integer, nullable=False)
    telegram_user_id = mapped_column(BigInteger, index=True, nullable=False)

    collection = relationship(
        "StickerCollection",
        backref="stickers",
        lazy="joined",
    )
    character = relationship(
        "StickerCharacter",
        backref="stickers",
        lazy="joined",
    )
