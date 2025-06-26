from core.models.rule import TelegramChatPremium
from tests.factories.rule.base import TelegramChatRuleBaseFactory


class TelegramChatPremiumFactory(TelegramChatRuleBaseFactory):
    class Meta:
        abstract = False
        model = TelegramChatPremium
        sqlalchemy_session_persistence = "flush"
