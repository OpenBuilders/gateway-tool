import factory
from factory.alchemy import SQLAlchemyModelFactory

from core.models.user import User


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "flush"

    telegram_id = factory.Sequence(lambda n: n + 1000000)
    username = factory.Sequence(lambda n: f"user{n}")
    first_name = factory.Sequence(lambda n: f"First{n}")
    last_name = factory.Sequence(lambda n: f"Last{n}")
    language = "en"
    is_blocked = False
    is_admin = False
    is_premium = False
    allows_write_to_pm = True
