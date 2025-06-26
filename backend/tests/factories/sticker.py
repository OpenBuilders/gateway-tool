import factory
from factory.alchemy import SQLAlchemyModelFactory

from core.models.sticker import StickerCollection, StickerCharacter


class StickerCollectionFactory(SQLAlchemyModelFactory):
    class Meta:
        model = StickerCollection
        sqlalchemy_session_persistence = "flush"

    id = factory.Sequence(lambda n: n + 1)
    title = factory.Faker(provider="pystr")
    description = factory.Faker(provider="text")
    logo_url = factory.Faker(provider="url")


class StickerCharacterFactory(SQLAlchemyModelFactory):
    class Meta:
        model = StickerCharacter
        sqlalchemy_session_persistence = "flush"

    id = factory.Sequence(lambda n: n + 1)
    external_id = factory.Sequence(lambda n: n + 1)
    collection_id = factory.SelfAttribute("collection.id")
    collection = factory.SubFactory("tests.factories.sticker.StickerCollectionFactory")
    name = factory.Faker(provider="pystr")
    description = factory.Faker(provider="text")
    supply = factory.Faker(provider="pyint")
    logo_url = factory.Faker(provider="url")
