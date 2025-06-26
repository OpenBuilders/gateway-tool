import factory

from core.models.rule import TelegramChatEmoji
from tests.factories.rule.base import TelegramChatRuleBaseFactory


class TelegramChatEmojiRuleFactory(TelegramChatRuleBaseFactory):
    class Meta:
        abstract = False
        model = TelegramChatEmoji
        sqlalchemy_session_persistence = "flush"

    emoji_id = factory.Faker("pystr", min_chars=10, max_chars=15)
