from core.models.rule import TelegramChatGiftCollection
from core.services.chat.rule.base import BaseTelegramChatRuleService


class TelegramChatGiftCollectionService(
    BaseTelegramChatRuleService[TelegramChatGiftCollection]
):
    model = TelegramChatGiftCollection
