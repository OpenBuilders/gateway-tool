import logging

from core.models.rule import TelegramChatRuleGroup
from core.services.base import BaseService


logger = logging.getLogger(__name__)


class TelegramChatRuleGroupService(BaseService):
    def get(self, chat_id: int, group_id: int) -> TelegramChatRuleGroup:
        return (
            self.db_session.query(TelegramChatRuleGroup)
            .filter(
                TelegramChatRuleGroup.chat_id == chat_id,
                TelegramChatRuleGroup.id == group_id,
            )
            .one()
        )

    def get_all(self, chat_id: int) -> list[TelegramChatRuleGroup]:
        return (
            self.db_session.query(TelegramChatRuleGroup)
            .filter(
                TelegramChatRuleGroup.chat_id == chat_id,
            )
            .order_by(TelegramChatRuleGroup.order)
            .all()
        )

    def get_default_for_chat(self, chat_id: int) -> TelegramChatRuleGroup:
        default_group = (
            self.db_session.query(TelegramChatRuleGroup)
            .filter(
                TelegramChatRuleGroup.chat_id == chat_id,
            )
            .order_by(TelegramChatRuleGroup.order)
            .first()
        )

        if not default_group:
            raise ValueError(f"No default group found for chat {chat_id!r}.")

        return default_group

    def create(self, chat_id: int) -> TelegramChatRuleGroup:
        current_max_order = (
            self.db_session.query(TelegramChatRuleGroup.order)
            .filter(TelegramChatRuleGroup.chat_id == chat_id)
            .order_by(TelegramChatRuleGroup.order.desc())
            .scalar()
            or 0
        )

        new_group = TelegramChatRuleGroup(
            chat_id=chat_id,
            order=current_max_order + 1,
        )
        self.db_session.add(new_group)
        self.db_session.commit()
        logger.info(f"Created a new rule group for chat {chat_id!r}.")
        return new_group

    def delete(self, chat_id: int, group_id: int) -> None:
        self.db_session.query(TelegramChatRuleGroup).filter(
            TelegramChatRuleGroup.chat_id == chat_id,
            TelegramChatRuleGroup.id == group_id,
        ).delete()
        self.db_session.commit()
        logger.info(f"Deleted rule group {group_id!r} for chat {chat_id!r}.")
