from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.orm import Session
from telethon.tl.types import ChatAdminRights

from community_manager.actions.chat import CommunityManagerChatAction
from tests.utils.misc import AsyncIterator
from core.actions.chat import TelegramChatAction
from core.constants import REQUIRED_BOT_PRIVILEGES
from core.dtos.chat import TelegramChatDTO
from core.exceptions.chat import TelegramChatNotSufficientPrivileges
from core.models.user import User
from tests.factories import TelegramChatUserFactory, TelegramChatFactory, UserFactory


def test_get_all_success(
    db_session: Session, mocked_telethon_client: MagicMock
) -> None:
    """Test successful retrieval of all chats managed by a user using real database objects."""
    # Arrange - Create real objects in the database using factories
    user = UserFactory.create(is_admin=True)

    # Create multiple chats
    chat1, chat2, chat3 = TelegramChatFactory.create_batch(3)

    TelegramChatUserFactory.create(chat=chat1, user=user, is_admin=True)
    TelegramChatUserFactory.create(chat=chat2, user=user, is_admin=True)
    TelegramChatUserFactory.create(chat=chat3, user=user)

    # Act
    action = TelegramChatAction(db_session, telethon_client=mocked_telethon_client)
    result = action.get_all(user)

    # Assert
    assert len(result) == 2
    assert all(isinstance(chat, TelegramChatDTO) for chat in result)
    assert {chat.id for chat in result} == {chat1.id, chat2.id}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("admin_rights", "should_raise"),
    [
        ({right: True for right in REQUIRED_BOT_PRIVILEGES}, False),
        ({right: False for right in REQUIRED_BOT_PRIVILEGES}, True),
    ],
)
async def test_get_chat_data_success(
    db_session: Session,
    mocked_telethon_client: MagicMock,
    mocked_telethon_chat: MagicMock,
    mocker: MockerFixture,
    admin_rights: dict[str, bool],
    should_raise: bool,
) -> None:
    mocked_telethon_chat.admin_rights = mocker.create_autospec(
        ChatAdminRights, **admin_rights
    )
    mocked_telethon_client.get_entity = mocker.AsyncMock(
        return_value=mocked_telethon_chat
    )

    # Act: Call `_get_chat_data`
    action = CommunityManagerChatAction(
        db_session, telethon_client=mocked_telethon_client
    )

    if should_raise:
        with pytest.raises(TelegramChatNotSufficientPrivileges):
            await action._get_chat_data(mocked_telethon_chat.id)
    else:
        result = await action._get_chat_data(mocked_telethon_chat.id)
        assert result.id == mocked_telethon_chat.id
        assert result.title == mocked_telethon_chat.title
        assert result.admin_rights == mocked_telethon_chat.admin_rights

    # Assert: Check if the mock methods were called and data was retrieved correctly
    mocked_telethon_client.get_entity.assert_called_once_with(mocked_telethon_chat.id)


@pytest.mark.asyncio
async def test_load_participants(
    db_session: Session,
    mocked_telethon_client: MagicMock,
    mocked_telethon_user: MagicMock,
    mocker: MockerFixture,
) -> None:
    # Arrange: Create a chat in the database
    chat = TelegramChatFactory()

    mocked_telethon_client.iter_participants = mocker.Mock(
        return_value=AsyncIterator([mocked_telethon_user])
    )

    # Act: Call `_load_participants`
    action = CommunityManagerChatAction(
        db_session, telethon_client=mocked_telethon_client
    )
    await action._load_participants(chat.id)

    # Assert: Verify the participant was added to the database
    user = (
        db_session.query(User).filter(User.telegram_id == mocked_telethon_user.id).one()
    )
    assert user.username == mocked_telethon_user.username


@pytest.mark.parametrize("sufficient_bot_privileges", [True, False])
@pytest.mark.asyncio
async def test_create_success(
    db_session: Session,
    mocked_telethon_chat_sufficient_rights: MagicMock,
    mocked_telethon_client: MagicMock,
    mocker: MockerFixture,
    sufficient_bot_privileges: bool,
):
    """Test successful creation of a Telegram chat."""
    # Arrange
    chat_identifier = -123456789
    chat_invite_link = "https://t.me/joinchat/123456789"
    mocked_telethon_chat_sufficient_rights.id = chat_identifier

    # Mock get_peer_id to return the chat_id
    mocker.patch("telethon.utils.get_peer_id", return_value=chat_identifier)

    mocked_telethon_client.get_entity = AsyncMock(
        return_value=mocked_telethon_chat_sufficient_rights
    )

    # Mock fetch_and_push_profile_photo to return None (no profile photo)
    mock_fetch_photo = AsyncMock(return_value=None)
    mocker.patch.object(
        CommunityManagerChatAction, "fetch_and_push_profile_photo", mock_fetch_photo
    )

    # Act
    action = CommunityManagerChatAction(
        db_session, telethon_client=mocked_telethon_client
    )
    action.telethon_service.get_invite_link = AsyncMock(
        return_value=MagicMock(link=chat_invite_link)
    )
    event = Mock()
    event.is_self = True
    event.sufficient_bot_privileges = sufficient_bot_privileges
    result = await action.create(chat_identifier, event=event)
    # Verify that the chat was created in the database
    assert isinstance(result, TelegramChatDTO)
    assert result.id == mocked_telethon_chat_sufficient_rights.id
    assert result.title == mocked_telethon_chat_sufficient_rights.title
    assert result.is_forum == mocked_telethon_chat_sufficient_rights.forum
    assert result.insufficient_privileges != sufficient_bot_privileges
    # We don't provide any mocked participants
    assert result.members_count == 0
