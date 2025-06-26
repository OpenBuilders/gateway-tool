from typing import TypeVar, Protocol
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from core.actions.chat import ManagedChatBaseAction
from core.models.user import User


ActionT = TypeVar("ActionT", bound=ManagedChatBaseAction)


class ChatManageActionFactory(Protocol):
    def __call__(
        self,
        action_cls: type[ActionT],
        db_session: Session,
        chat_slug: str,
        requestor: User,
    ) -> ActionT:
        ...


@pytest.fixture(scope="session")
def mocked_managed_chat_action_factory() -> ChatManageActionFactory:
    def inner(
        action_cls: type[ActionT],
        db_session: Session,
        chat_slug: str,
        requestor: User,
    ) -> ActionT:
        """
        A pytest fixture that creates and returns a factory function for testing
        `ManagedChatBaseAction` instances. The fixture constructs an instance of the
        specified action class using the provided database session, chat slug,
        and requestor. It also mocks the `is_chat_admin` method of the
        `telegram_chat_user_service` in the action to always return `True`.

        :param action_cls: The `ManagedChatBaseAction` class to instantiate.
        :param db_session: The SQLAlchemy session to use in the action.
        :param chat_slug: The unique identifier for a chat to associate with the action.
        :param requestor: The user initiating the action.
        :return: A factory function that produces instances of `action_cls` with mocked
                 dependencies.
        """
        with patch(
            "core.services.chat.user.TelegramChatUserService.is_chat_admin",
            return_value=True,
        ):
            action = action_cls(
                db_session=db_session,
                chat_slug=chat_slug,
                requestor=requestor,
            )
        return action

    return inner
