import factory
from factory.alchemy import SQLAlchemyModelFactory

from core.models.blockchain import Jetton


class JettonFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Jetton
        sqlalchemy_session_persistence = "flush"

    address = factory.Faker("pystr", min_chars=65, max_chars=65, prefix="0:")
    name = factory.Faker("cryptocurrency_name")
    description = factory.Faker("text")
    symbol = factory.Faker("cryptocurrency_code")
    total_supply = factory.Faker("pyint")
    logo_path = factory.Faker("image_url")
    is_enabled = True
