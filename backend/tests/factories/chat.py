import factory
from factory.alchemy import SQLAlchemyModelFactory

from core.models.chat import TelegramChat, TelegramChatUser


class TelegramChatFactory(SQLAlchemyModelFactory):
    class Meta:
        model = TelegramChat
        sqlalchemy_session_persistence = "flush"

    id = factory.Sequence(lambda n: n + 1)
    title = factory.Sequence(lambda n: f"Chat {n}")
    slug = factory.Sequence(lambda n: f"chat-{n}")
    username = factory.Sequence(lambda n: f"chat{n}")
    description = factory.Sequence(lambda n: f"Description for Chat {n}")
    is_forum = False
    is_enabled = True
    is_full_control = True
    insufficient_privileges = False
    logo_path = None
    invite_link = factory.Sequence(lambda n: f"https://t.me/+{n}")


class TelegramChatUserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = TelegramChatUser
        sqlalchemy_session_persistence = "flush"

    user_id = factory.SelfAttribute("user.id")
    user = factory.SubFactory("tests.factories.user.UserFactory")
    chat_id = factory.SelfAttribute("chat.id")
    chat = factory.SubFactory("tests.factories.chat.TelegramChatFactory")
    is_admin = False
    is_managed = True
    created_at = factory.Faker("date_time_this_year")
