
# Testing Guidelines for Access Tool Backend

This document outlines the testing strategy for the Access Tool backend, including unit tests, functional tests, and integration with the MySQL database.

## Table of Contents
1. [Testing Framework](#testing-framework)
2. [Directory Structure](#directory-structure)
3. [Test Types](#test-types)
4. [Database Testing](#database-testing)
5. [Fixtures and Factories](#fixtures-and-factories)
6. [Mocking](#mocking)
7. [Running Tests](#running-tests)
8. [Example Tests](#example-tests)

## Testing Framework

We'll use the following tools for testing:

- **pytest**: Main testing framework
- **pytest-cov**: For test coverage reporting
- **pytest-mock**: For mocking dependencies
- **factory-boy**: For creating test data
- **pytest-asyncio**: For testing async code
- **pytest-env**: For environment variable management

## Directory Structure

The test directory structure should mirror the application structure:

```
backend/
├── tests/
│   ├── conftest.py                 # Shared fixtures
│   ├── factories/                  # Factory Boy factories
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── chat.py
│   │   └── rule.py
│   ├── unit/                       # Unit tests
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── actions/
│   │   │   ├── models/
│   │   │   └── services/
│   │   ├── api/
│   │   ├── community_manager/
│   │   ├── indexer/
│   │   └── scheduler/
│   └── functional/                 # Functional tests
│       ├── __init__.py
│       ├── api/
│       ├── community_manager/
│       └── indexer/
```

## Test Types

### Unit Tests

Unit tests should test individual components in isolation. Mock external dependencies.

Focus areas:
- Service methods
- Action classes
- Model methods
- Utility functions

### Functional Tests

Functional tests should test the integration between components and verify that the system works as expected.

Focus areas:
- API endpoints
- End-to-end workflows
- Database interactions

## Database Testing

We'll use the existing MySQL Docker service for testing. The test database should be separate from the development database.

1. Create a test database configuration in `conftest.py`
2. Use pytest fixtures to set up and tear down the database for each test
3. Use transactions to roll back changes after each test

Example database fixture:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.db import Base

@pytest.fixture(scope="session")
def db_engine():
    # Use the MySQL Docker service
    engine = create_engine("mysql+pymysql://root:password@localhost:3307/access_test")
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(db_engine):
    # Create all tables
    Base.metadata.create_all(db_engine)
    
    # Create a new session
    Session = sessionmaker(bind=db_engine)
    session = Session()
    
    yield session
    
    # Roll back all changes and close the session
    session.rollback()
    session.close()
    
    # Drop all tables
    Base.metadata.drop_all(db_engine)
```

## Fixtures and Factories

We'll use Factory Boy to create test data. Factories should be defined for all models.

Example User factory:

```python
import factory
from factory.alchemy import SQLAlchemyModelFactory
from core.models.user import User

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"
    
    id = factory.Sequence(lambda n: n)
    username = factory.Sequence(lambda n: f"user{n}")
    telegram_id = factory.Sequence(lambda n: n + 1000000)
    is_admin = False
    is_active = True
```

Example Chat factory:

```python
import factory
from factory.alchemy import SQLAlchemyModelFactory
from core.models.chat import TelegramChat

class TelegramChatFactory(SQLAlchemyModelFactory):
    class Meta:
        model = TelegramChat
        sqlalchemy_session_persistence = "commit"
    
    id = factory.Sequence(lambda n: n)
    title = factory.Sequence(lambda n: f"Chat {n}")
    slug = factory.Sequence(lambda n: f"chat-{n}")
    is_forum = False
    is_enabled = True
```

## Mocking

Use pytest-mock to mock external dependencies:

- HTTP requests
- Telegram API calls
- External services

Example:

```python
def test_telegram_chat_emoji_action_create(mocker, db_session):
    # Mock the service method
    mock_service = mocker.patch("core.services.chat.rule.emoji.TelegramChatEmojiService")
    mock_service.return_value.exists.return_value = False
    
    # Test the action
    action = TelegramChatEmojiAction(db_session, user, "chat-slug")
    result = action.create("emoji_id")
    
    # Assert the result
    assert result.type == EligibilityCheckType.EMOJI
    assert result.title == "Emoji Status"
```

## Running Tests

Add the following to your `setup.cfg` or `pytest.ini`:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
python_classes = Test*
addopts = --cov=backend --cov-report=term-missing
```

Run tests with:

```bash
pytest
```

## Example Tests

### Unit Test Example for TelegramChatEmojiAction

```python
import pytest
from fastapi import HTTPException
from sqlalchemy.exc import NoResultFound

from core.actions.chat.rule.emoji import TelegramChatEmojiAction
from core.dtos.chat.rule import ChatEligibilityRuleDTO, EligibilityCheckType
from core.models.rule import TelegramChatEmoji
from tests.factories.user import UserFactory
from tests.factories.chat import telegram_chat_factory_builder
from tests.factories.rule import TelegramChatEmojiFactory


class TestTelegramChatEmojiAction:
    def test_read_success(self, db_session, mocker):
        # Arrange
        user = UserFactory(db_session=db_session, is_admin=True)
        chat = telegram_chat_factory_builder(db_session=db_session)
        rule = TelegramChatEmojiFactory(db_session=db_session, chat_id=chat.id)

        # Mock the chat user service to return True for is_chat_admin
        mocker.patch(
            "core.services.chat.user.TelegramChatUserService.is_chat_admin",
            return_value=True
        )

        # Act
        action = TelegramChatEmojiAction(db_session, user, chat.slug)
        result = action.read(rule.id)

        # Assert
        assert isinstance(result, ChatEligibilityRuleDTO)
        assert result.id == rule.id
        assert result.type == EligibilityCheckType.EMOJI
        assert result.is_enabled == rule.is_enabled

    def test_read_not_found(self, db_session, mocker):
        # Arrange
        user = UserFactory(db_session=db_session, is_admin=True)
        chat = telegram_chat_factory_builder(db_session=db_session)

        # Mock the chat user service to return True for is_chat_admin
        mocker.patch(
            "core.services.chat.user.TelegramChatUserService.is_chat_admin",
            return_value=True
        )

        # Mock the service to raise NoResultFound
        mocker.patch(
            "core.services.chat.rule.emoji.TelegramChatEmojiService.get",
            side_effect=NoResultFound()
        )

        # Act & Assert
        action = TelegramChatEmojiAction(db_session, user, chat.slug)
        with pytest.raises(HTTPException) as exc_info:
            action.read(999)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Rule not found"

    def test_create_success(self, db_session, mocker):
        # Arrange
        user = UserFactory(db_session=db_session, is_admin=True)
        chat = telegram_chat_factory_builder(db_session=db_session)
        emoji_id = "emoji123"

        # Mock the chat user service to return True for is_chat_admin
        mocker.patch(
            "core.services.chat.user.TelegramChatUserService.is_chat_admin",
            return_value=True
        )

        # Mock the service to return False for exists
        mocker.patch(
            "core.services.chat.rule.emoji.TelegramChatEmojiService.exists",
            return_value=False
        )

        # Mock the service to return a rule
        mock_rule = TelegramChatEmoji(id=1, chat_id=chat.id, emoji_id=emoji_id, is_enabled=True)
        mocker.patch(
            "core.services.chat.rule.emoji.TelegramChatEmojiService.create",
            return_value=mock_rule
        )

        # Act
        action = TelegramChatEmojiAction(db_session, user, chat.slug)
        result = action.create(emoji_id)

        # Assert
        assert isinstance(result, ChatEligibilityRuleDTO)
        assert result.type == EligibilityCheckType.STICKER_COLLECTION
        assert result.title == "Emoji Status"
```

### Functional Test Example for API Endpoint

```python
import pytest
from fastapi.testclient import TestClient
from api.app import app
from tests.factories.user import UserFactory
from tests.factories.chat import telegram_chat_factory_builder

client = TestClient(app)


def test_create_emoji_rule(db_session, mocker):
    # Arrange
    user = UserFactory(db_session=db_session, is_admin=True)
    chat = telegram_chat_factory_builder(db_session=db_session)

    # Mock authentication
    mocker.patch(
        "api.deps.validate_access_token",
        return_value=user
    )

    # Act
    response = client.post(
        f"/api/v1/chats/{chat.slug}/rules/emoji",
        json={"emoji_id": "emoji123"}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "sticker_collection"
    assert data["title"] == "Emoji Status"
    assert data["is_enabled"] is True
```

This testing structure provides a comprehensive approach to testing the backend components of the Access Tool project, ensuring code quality and reliability.