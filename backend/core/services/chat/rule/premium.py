from core.models.rule import TelegramChatPremium
from core.services.chat.rule.base import BaseTelegramChatRuleService


class TelegramChatPremiumService(BaseTelegramChatRuleService):
    model = TelegramChatPremium

    def exists(self, chat_id: int) -> bool:
        return (
            self.db_session.query(TelegramChatPremium)
            .filter(TelegramChatPremium.chat_id == chat_id)
            .count()
            > 0
        )
