import factory

from core.models.rule import TelegramChatStickerCollection
from tests.factories.base import BaseSQLAlchemyModelFactory


class TelegramChatRuleBaseFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "commit"

    id = factory.Sequence(lambda n: n + 1)
    group_id = factory.SelfAttribute("group.id")
    group = factory.SubFactory(
        "tests.factories.rule.group.TelegramChatRuleGroupFactory"
    )
    is_enabled = True
    grants_write_access = True
    created_at = factory.Faker("date_time_this_year")


class TelegramChatThresholdRuleMixin(BaseSQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "commit"

    threshold = 1


class TelegramChatStickerCollectionFactory(
    TelegramChatRuleBaseFactory, TelegramChatThresholdRuleMixin
):
    class Meta:
        abstract = False
        model = TelegramChatStickerCollection
        sqlalchemy_session_persistence = "commit"

    chat_id = factory.SelfAttribute("chat.id")
    chat = factory.SubFactory("tests.factories.chat.TelegramChatFactory")
    collection_id = factory.SelfAttribute("collection.id")
    collection = factory.SubFactory("tests.factories.sticker.StickerCollectionFactory")
    character_id = factory.SelfAttribute("character.id")
    character = factory.SubFactory("tests.factories.sticker.StickerCharacterFactory")
