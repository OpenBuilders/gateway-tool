import logging

from fastapi import HTTPException
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from core.actions.chat import ManagedChatBaseAction
from core.dtos.chat.rule.emoji import (
    EmojiChatEligibilityRuleDTO,
    CreateTelegramChatEmojiRuleDTO,
    UpdateTelegramChatEmojiRuleDTO,
)
from core.models.user import User
from core.services.chat.rule.emoji import TelegramChatEmojiService


logger = logging.getLogger(__name__)


class TelegramChatEmojiAction(ManagedChatBaseAction):
    def __init__(self, db_session: Session, requestor: User, chat_slug: str):
        super().__init__(db_session, requestor, chat_slug)
        self.service = TelegramChatEmojiService(db_session)

    def read(self, rule_id: int) -> EmojiChatEligibilityRuleDTO:
        try:
            rule = self.service.get(chat_id=self.chat.id, id_=rule_id)
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )
        return EmojiChatEligibilityRuleDTO.from_orm(rule)

    def check_duplicates(
        self, chat_id: int, group_id: int, emoji_id: str, entity_id: int | None = None
    ) -> None:
        """
        Checks and prevents the creation of duplicate rules with the same `emoji_id` for a
        specific `chat_id` and `group_id`.
        Raises an HTTP exception if duplication is detected.

        :param chat_id: The ID of the chat where the rule is being applied.
        :param group_id: The ID of the group where the rule is being applied.
        :param emoji_id: The ID of the emoji being checked for duplication.
        :param entity_id: The ID of the existing entity being modified, if applicable. This parameter
            allows modifications to bypass duplication check against itself. Defaults to None.

        :raises HTTPException: If another rule with the same `emoji_id` already exists in the specified
            `chat_id` and `group_id`.
        """
        existing_rules = self.service.find(
            chat_id=chat_id, group_id=group_id, emoji_id=emoji_id
        )
        if next(filter(lambda rule: rule.id != entity_id, existing_rules), None):
            raise HTTPException(
                detail="Rule with provided emoji already exists for that chat. Please, modify it instead.",
                status_code=HTTP_400_BAD_REQUEST,
            )

    def create(
        self, emoji_id: str, group_id: int | None
    ) -> EmojiChatEligibilityRuleDTO:
        if self.service.exists(chat_id=self.chat.id):
            raise HTTPException(
                detail="Telegram Emoji rule already exists for that chat. Please, modify it instead.",
                status_code=HTTP_400_BAD_REQUEST,
            )

        group_id = self.resolve_group_id(chat_id=self.chat.id, group_id=group_id)
        self.check_duplicates(
            chat_id=self.chat.id, group_id=group_id, emoji_id=emoji_id
        )

        rule = self.service.create(
            CreateTelegramChatEmojiRuleDTO(
                chat_id=self.chat.id,
                group_id=group_id,
                emoji_id=emoji_id,
                is_enabled=True,
            )
        )
        logger.info(f"New Telegram Emoji rule created for the chat {self.chat.id!r}.")
        return EmojiChatEligibilityRuleDTO.from_orm(rule)

    def update(
        self,
        rule_id: int,
        emoji_id: str,
        is_enabled: bool,
    ) -> EmojiChatEligibilityRuleDTO:
        try:
            rule = self.service.get(chat_id=self.chat.id, id_=rule_id)
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )

        self.check_duplicates(
            chat_id=self.chat.id, group_id=rule.group_id, emoji_id=emoji_id
        )

        self.service.update(
            rule=rule,
            dto=UpdateTelegramChatEmojiRuleDTO(
                emoji_id=emoji_id, is_enabled=is_enabled
            ),
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
