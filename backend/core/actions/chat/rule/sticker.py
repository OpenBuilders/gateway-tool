import logging

from fastapi import HTTPException
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from core.actions.chat import ManagedChatBaseAction
from core.dtos.chat.rule.sticker import (
    StickerChatEligibilityRuleDTO,
    CreateTelegramChatStickerCollectionRuleDTO,
    UpdateTelegramChatStickerCollectionRuleDTO,
)
from core.models.user import User
from core.services.chat.rule.sticker import TelegramChatStickerCollectionService


logger = logging.getLogger(__name__)


class TelegramChatStickerCollectionAction(ManagedChatBaseAction):
    def __init__(self, db_session: Session, requestor: User, chat_slug: str):
        super().__init__(db_session, requestor, chat_slug)
        self.telegram_chat_sticker_collection_service = (
            TelegramChatStickerCollectionService(db_session)
        )

    async def read(self, rule_id: int) -> StickerChatEligibilityRuleDTO:
        try:
            rule = self.telegram_chat_sticker_collection_service.get(
                id_=rule_id, chat_id=self.chat.id
            )
        except NoResultFound:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Rule not found")

        return StickerChatEligibilityRuleDTO.from_orm(rule)

    def check_duplicates(
        self,
        chat_id: int,
        group_id: int,
        collection_id: int | None,
        character_id: int | None,
        category: str | None,
        entity_id: int | None = None,
    ) -> None:
        """
        Checks for duplicate rules based on the provided parameters. It searches for
        existing rules matching the specified criteria and ensures that no duplicate
        rule exists in the database.

        :param chat_id: The identifier of the chat to check for duplicate rules.
        :param group_id: The identifier of the group to check for duplicate rules.
        :param collection_id: The identifier of the sticker collection to check
            against or None.
        :param character_id: The identifier of the character to check against or None.
        :param category: The category to check against or None.
        :param entity_id: The identifier of the entity being checked. This is used to
            exclude the entity itself from the duplicate check or None.
        :raises HTTPException: When a duplicate rule already exists in the database.
        :return: None. The function will raise an exception if a duplicate exists.
        """
        existing_rules = self.telegram_chat_sticker_collection_service.find(
            chat_id=chat_id,
            group_id=group_id,
            collection_id=collection_id,
            character_id=character_id,
            category=category,
        )
        if next(filter(lambda rule: rule.id != entity_id, existing_rules), None):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Duplicate rule already exists",
            )

    async def create(
        self,
        group_id: int | None,
        collection_id: int | None,
        character_id: int | None,
        category: None,
        threshold: int,
    ) -> StickerChatEligibilityRuleDTO:
        group_id = self.resolve_group_id(chat_id=self.chat.id, group_id=group_id)
        self.check_duplicates(
            chat_id=self.chat.id,
            group_id=group_id,
            collection_id=collection_id,
            character_id=character_id,
            category=category,
        )

        new_rule = self.telegram_chat_sticker_collection_service.create(
            CreateTelegramChatStickerCollectionRuleDTO(
                chat_id=self.chat.id,
                group_id=group_id,
                collection_id=collection_id,
                character_id=character_id,
                category=category,
                threshold=threshold,
                is_enabled=True,
            )
        )
        logger.info(
            f"New Telegram Chat Sticker Collection rule created for the chat {self.chat.id!r}."
        )
        return StickerChatEligibilityRuleDTO.from_orm(new_rule)

    async def update(
        self,
        rule_id: int,
        collection_id: int | None,
        character_id: int | None,
        category: None,
        threshold: int,
        is_enabled: bool,
    ) -> StickerChatEligibilityRuleDTO:
        try:
            rule = self.telegram_chat_sticker_collection_service.get(
                id_=rule_id, chat_id=self.chat.id
            )
        except NoResultFound:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Rule not found")

        self.check_duplicates(
            chat_id=self.chat.id,
            group_id=rule.group_id,
            collection_id=collection_id,
            character_id=character_id,
            category=category,
            entity_id=rule_id,
        )

        updated_rule = self.telegram_chat_sticker_collection_service.update(
            rule=rule,
            dto=UpdateTelegramChatStickerCollectionRuleDTO(
                collection_id=collection_id,
                character_id=character_id,
                category=category,
                threshold=threshold,
                is_enabled=is_enabled,
            ),
        )
        logger.info(
            f"Updated Telegram Chat Sticker Collection rule {rule_id!r} for the chat {self.chat.id!r}."
        )
        return StickerChatEligibilityRuleDTO.from_orm(updated_rule)

    async def delete(self, rule_id: int) -> None:
        self.telegram_chat_sticker_collection_service.delete(
            rule_id=rule_id,
            chat_id=self.chat.id,
        )
        logger.info(
            f"Deleted Telegram Chat Sticker Collection rule {rule_id!r} for the chat {self.chat.id!r}."
        )
