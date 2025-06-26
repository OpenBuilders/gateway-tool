import factory

from core.models.rule import TelegramChatStickerCollection
from tests.factories.rule.base import (
    TelegramChatRuleBaseFactory,
    TelegramChatThresholdRuleMixin,
)


class TelegramChatStickerCollectionFactory(
    TelegramChatRuleBaseFactory, TelegramChatThresholdRuleMixin
):
    class Meta:
        abstract = False
        model = TelegramChatStickerCollection
        sqlalchemy_session_persistence = "flush"

    collection_id = factory.SelfAttribute("collection.id")
    collection = factory.SubFactory("tests.factories.sticker.StickerCollectionFactory")
    character_id = factory.SelfAttribute("character.id")
    character = factory.SubFactory("tests.factories.sticker.StickerCharacterFactory")
