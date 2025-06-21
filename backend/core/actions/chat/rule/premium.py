import logging

from fastapi import HTTPException
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from core.actions.chat import ManagedChatBaseAction
from core.dtos.chat.rule import ChatEligibilityRuleDTO
from core.dtos.chat.rule.premium import (
    CreateTelegramChatPremiumRuleDTO,
    UpdateTelegramChatPremiumRuleDTO,
)
from core.models.user import User
from core.services.chat.rule.premium import TelegramChatPremiumService


logger = logging.getLogger(__name__)


class TelegramChatPremiumAction(ManagedChatBaseAction):
    def __init__(self, db_session: Session, requestor: User, chat_slug: str):
        super().__init__(db_session, requestor, chat_slug)
        self.service = TelegramChatPremiumService(db_session)

    def read(self, rule_id: int) -> ChatEligibilityRuleDTO:
        try:
            rule = self.service.get(chat_id=self.chat.id, id_=rule_id)
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )
        return ChatEligibilityRuleDTO.from_premium_rule(rule)

    def check_duplicates(
        self, chat_id: int, group_id: int, entity_id: int | None = None
    ) -> None:
        """
        Checks for duplicate rules based on the provided chat ID, group ID, and
        optional entity ID. If a duplicate rule exists, raises an HTTPException.

        :param chat_id: The ID of the chat.
        :param group_id: The ID of the group.
        :param entity_id: Optional ID of the entity to exclude from duplicate
                          checking.
        :raises HTTPException: If a rule with the provided group already exists
                               for the given chat.
        """
        existing_rules = self.service.find(chat_id=chat_id, group_id=group_id)
        if next(filter(lambda rule: rule.id != entity_id, existing_rules), None):
            raise HTTPException(
                detail="Rule with provided group already exists for that chat. Please, modify it instead.",
                status_code=HTTP_400_BAD_REQUEST,
            )

    def create(self, group_id: int | None) -> ChatEligibilityRuleDTO:
        group_id = self.resolve_group_id(chat_id=self.chat.id, group_id=group_id)
        self.check_duplicates(chat_id=self.chat.id, group_id=group_id)

        rule = self.service.create(
            CreateTelegramChatPremiumRuleDTO(
                chat_id=self.chat.id, group_id=group_id, is_enabled=True
            )
        )
        logger.info(f"New Telegram Premium rule created for the chat {self.chat.id!r}.")
        return ChatEligibilityRuleDTO.from_premium_rule(rule)

    def update(self, rule_id: int, is_enabled: bool) -> ChatEligibilityRuleDTO:
        try:
            rule = self.service.get(chat_id=self.chat.id, id_=rule_id)
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )

        self.service.update(
            rule=rule, dto=UpdateTelegramChatPremiumRuleDTO(is_enabled=is_enabled)
        )
        logger.info(
            f"Updated Telegram Premium rule {rule_id!r} for the chat {self.chat.id!r}."
        )
        return ChatEligibilityRuleDTO.from_premium_rule(rule)

    def delete(self, rule_id: int) -> None:
        self.service.delete(chat_id=self.chat.id, rule_id=rule_id)
        logger.info(
            f"Deleted Telegram Premium rule {rule_id!r} for the chat {self.chat.id!r}."
        )
