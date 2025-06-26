import factory

from tests.factories.base import BaseSQLAlchemyModelFactory


class TelegramChatRuleBaseFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "flush"

    id = factory.Sequence(lambda n: n + 1)
    group_id = factory.SelfAttribute("group.id")
    group = factory.SubFactory(
        "tests.factories.rule.group.TelegramChatRuleGroupFactory"
    )
    chat_id = factory.SelfAttribute("chat.id")
    chat = factory.SubFactory("tests.factories.chat.TelegramChatFactory")
    is_enabled = True
    grants_write_access = True
    created_at = factory.Faker("date_time_this_year")


class TelegramChatThresholdRuleMixin(BaseSQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "flush"

    threshold = 1
