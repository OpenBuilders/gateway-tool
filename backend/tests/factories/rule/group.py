import factory
from factory.alchemy import SQLAlchemyModelFactory

from core.models.rule import TelegramChatRuleGroup


class TelegramChatRuleGroupFactory(SQLAlchemyModelFactory):
    class Meta:
        model = TelegramChatRuleGroup
        sqlalchemy_session_persistence = "flush"

    id = factory.Sequence(lambda n: n + 1)
    chat_id = factory.SelfAttribute("chat.id")
    chat = factory.SubFactory("tests.factories.chat.TelegramChatFactory")
    order = factory.Sequence(lambda n: n + 1)
    created_at = factory.Faker("date_time_this_year")
