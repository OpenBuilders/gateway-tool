import logging
from tempfile import NamedTemporaryFile

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from core.actions.chat import ManagedChatBaseAction
from core.dtos.chat.rules.emoji import EmojiChatEligibilityRuleDTO
from core.models.user import User
from core.services.cdn import CDNService
from core.services.chat.rule.emoji import TelegramChatEmojiService
from core.services.superredis import RedisService
from core.services.supertelethon import TelethonService
from core.settings import core_settings

logger = logging.getLogger(__name__)


class StickerSetDTO(BaseModel):
    id: int
    access_hash: int
    title: str
    short_name: str
    text_color: bool


class EmojiItemDTO(BaseModel):
    id: int
    access_hash: int
    mime_type: str
    logo_url: str
    sticker_set: StickerSetDTO


EMOJI_CACHE_KEY_TEMPLATE = "emoji-metadata:{emoji_id}"
EMOJI_CACHE_TTL = 60 * 60 * 24 * 30 * 12 * 10  # 10 years


class TelegramChatEmojiAction(ManagedChatBaseAction):
    def __init__(self, db_session: Session, requestor: User, chat_slug: str):
        super().__init__(db_session, requestor, chat_slug)
        self.service = TelegramChatEmojiService(db_session)
        self.telethon_service = TelethonService(
            bot_token=core_settings.telegram_bot_token
        )
        self.redis_service = RedisService()
        self.cdn_service = CDNService()

    async def get_cached_emoji_data(self, emoji_id: int) -> EmojiItemDTO:
        emoji_cache_key = EMOJI_CACHE_KEY_TEMPLATE.format(emoji_id=emoji_id)
        if cached_data := self.redis_service.get(emoji_cache_key):
            return EmojiItemDTO.model_validate_json(cached_data)

        await self.telethon_service.start()

        emoji, sticker_set = await self.telethon_service.index_emoji(emoji_id=emoji_id)
        with NamedTemporaryFile(mode="w+b", delete=True) as f:
            logo_path = await self.telethon_service.download_emoji(
                emoji=emoji, target_location=f
            )
            if logo_path:
                await self.cdn_service.upload_file(
                    file_path=f.name,
                    object_name=logo_path,
                )
                logger.info(f"Uploaded new emoji logo to {logo_path!r}.")

        await self.telethon_service.stop()

        emoji_item = EmojiItemDTO(
            id=emoji.id,
            access_hash=emoji.access_hash,
            mime_type=emoji.mime_type,
            logo_url=logo_path,
            sticker_set=StickerSetDTO(
                id=sticker_set.id,
                access_hash=sticker_set.access_hash,
                title=sticker_set.title,
                short_name=sticker_set.short_name,
                text_color=sticker_set.text_color,
            ),
        )
        self.redis_service.set(
            emoji_cache_key,
            emoji_item.model_dump_json(),
            EMOJI_CACHE_TTL,
        )
        return emoji_item

    def read(self, rule_id: int) -> EmojiChatEligibilityRuleDTO:
        try:
            rule = self.service.get(chat_id=self.chat.id, rule_id=rule_id)
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )
        return EmojiChatEligibilityRuleDTO.from_orm(rule)

    async def create(self, emoji_id: int) -> EmojiChatEligibilityRuleDTO:
        if self.service.exists(chat_id=self.chat.id):
            raise HTTPException(
                detail="Telegram Emoji rule already exists for that chat. Please, modify it instead.",
                status_code=HTTP_400_BAD_REQUEST,
            )

        emoji_data = await self.get_cached_emoji_data(emoji_id=emoji_id)
        rule = self.service.create(
            chat_id=self.chat.id, emoji_id=emoji_id, logo_url=emoji_data.logo_url
        )
        logger.info(f"New Telegram Emoji rule created for the chat {self.chat.id!r}.")
        return EmojiChatEligibilityRuleDTO.from_orm(rule)

    async def update(
        self, rule_id: int, emoji_id: int, is_enabled: bool
    ) -> EmojiChatEligibilityRuleDTO:
        try:
            rule = self.service.get(chat_id=self.chat.id, rule_id=rule_id)
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )

        emoji_data = await self.get_cached_emoji_data(emoji_id=emoji_id)
        self.service.update(
            rule=rule,
            emoji_id=emoji_id,
            is_enabled=is_enabled,
            logo_url=emoji_data.logo_url,
        )
        logger.info(
            f"Updated Telegram Emoji rule {rule_id!r} for the chat {self.chat.id!r}."
        )
        return EmojiChatEligibilityRuleDTO.from_orm(rule)

    def delete(self, rule_id: int) -> None:
        self.service.delete(chat_id=self.chat.id, rule_id=rule_id)
        logger.info(
            f"Deleted Telegram Emoji rule {rule_id!r} for the chat {self.chat.id!r}."
        )
