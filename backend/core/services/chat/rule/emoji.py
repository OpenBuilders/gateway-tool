from core.models.rule import TelegramChatEmoji
from core.services.chat.rule.base import BaseTelegramChatRuleService


class TelegramChatEmojiService(BaseTelegramChatRuleService[TelegramChatEmoji]):
    model = TelegramChatEmoji

    def exists(self, chat_id: int) -> bool:
        return (
            self.db_session.query(TelegramChatEmoji)
            .filter(TelegramChatEmoji.chat_id == chat_id)
            .count()
            > 0
        )
