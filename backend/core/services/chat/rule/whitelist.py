import logging
from typing import Generic

from core.models.rule import TelegramChatWhitelistExternalSource, TelegramChatWhitelist
from core.services.chat.rule.base import BaseTelegramChatRuleService, TelegramChatRuleT

logger = logging.getLogger(__name__)


class BaseTelegramChatExternalSourceService(
    BaseTelegramChatRuleService,
    Generic[TelegramChatRuleT],
):
    def set_content(
        self, rule: TelegramChatRuleT, content: list[int]
    ) -> TelegramChatRuleT:
        rule.content = content
        self.db_session.commit()
        return rule


class TelegramChatExternalSourceService(
    BaseTelegramChatExternalSourceService[TelegramChatWhitelistExternalSource]
):
    model = TelegramChatWhitelistExternalSource


class TelegramChatWhitelistService(
    BaseTelegramChatExternalSourceService[TelegramChatWhitelist]
):
    model = TelegramChatWhitelist
