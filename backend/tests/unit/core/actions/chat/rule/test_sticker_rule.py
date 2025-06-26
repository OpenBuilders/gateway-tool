import pytest
from sqlalchemy.orm import Session

from core.actions.chat.rule.sticker import TelegramChatStickerCollectionAction
from core.dtos.chat.rule.sticker import StickerChatEligibilityRuleDTO
from core.models.rule import TelegramChatStickerCollection, TelegramChatRuleGroup
from tests.factories import TelegramChatFactory, UserFactory
from tests.factories.rule.group import TelegramChatRuleGroupFactory
from tests.factories.rule.sticker import TelegramChatStickerCollectionFactory
from tests.factories.sticker import StickerCollectionFactory, StickerCharacterFactory
from tests.fixtures.action import ChatManageActionFactory


@pytest.mark.asyncio
async def test_create_sticker_rule__pass(
    db_session: Session,
    mocked_managed_chat_action_factory: ChatManageActionFactory,
):
    sticker_collection = StickerCollectionFactory.create()
    sticker_character = StickerCharacterFactory.create(collection=sticker_collection)

    chat = TelegramChatFactory.create()
    group = TelegramChatRuleGroupFactory.create(chat=chat)

    requestor = UserFactory.create()

    action = mocked_managed_chat_action_factory(
        action_cls=TelegramChatStickerCollectionAction,
        db_session=db_session,
        chat_slug=chat.slug,
        requestor=requestor,
    )
    assert (
        db_session.query(TelegramChatStickerCollection).first() is None
    ), "There is already an existing rule."
    result = await action.create(
        group_id=group.id,
        collection_id=sticker_collection.id,
        character_id=sticker_character.id,
        category=None,
        threshold=1,
    )
    assert isinstance(result, StickerChatEligibilityRuleDTO)

    existing_rule = db_session.query(TelegramChatStickerCollection).one()
    assert existing_rule.collection_id == sticker_collection.id
    assert existing_rule.character_id == sticker_character.id
    assert existing_rule.category is None
    assert existing_rule.threshold == 1


@pytest.mark.asyncio
async def test_create_sticker_rule__empty_group__group_created(
    db_session: Session,
    mocked_managed_chat_action_factory: ChatManageActionFactory,
) -> None:
    sticker_collection = StickerCollectionFactory.create()
    sticker_character = StickerCharacterFactory.create(collection=sticker_collection)

    chat = TelegramChatFactory.create()

    requestor = UserFactory.create()

    action = mocked_managed_chat_action_factory(
        action_cls=TelegramChatStickerCollectionAction,
        db_session=db_session,
        chat_slug=chat.slug,
        requestor=requestor,
    )

    result = await action.create(
        group_id=None,
        collection_id=sticker_collection.id,
        character_id=sticker_character.id,
        category=None,
        threshold=1,
    )

    assert isinstance(result, StickerChatEligibilityRuleDTO)

    new_rule = db_session.query(TelegramChatStickerCollection).one()
    new_group = db_session.query(TelegramChatRuleGroup).one()

    assert new_rule.collection_id == sticker_collection.id
    assert new_rule.character_id == sticker_character.id
    assert new_rule.category is None
    assert new_rule.threshold == 1
    assert new_rule.group_id == new_group.id, "Group ID should be set."


@pytest.mark.asyncio
async def test_update_sticker_rule__pass(
    db_session: Session,
    mocked_managed_chat_action_factory: ChatManageActionFactory,
):
    telegram_chat_sticker_collection_rule = (
        TelegramChatStickerCollectionFactory.with_session(db_session).create()
    )

    another_sticker_collection = StickerCollectionFactory.create()
    another_sticker_character = StickerCharacterFactory.create(
        collection=another_sticker_collection
    )

    requestor = UserFactory.create()

    action = mocked_managed_chat_action_factory(
        action_cls=TelegramChatStickerCollectionAction,
        db_session=db_session,
        chat_slug=telegram_chat_sticker_collection_rule.chat.slug,
        requestor=requestor,
    )

    existing_rule = db_session.query(TelegramChatStickerCollection).one()
    assert (
        existing_rule.collection_id
        == telegram_chat_sticker_collection_rule.collection_id
    )
    assert (
        existing_rule.character_id == telegram_chat_sticker_collection_rule.character_id
    )

    result = await action.update(
        rule_id=telegram_chat_sticker_collection_rule.id,
        collection_id=another_sticker_collection.id,
        character_id=another_sticker_character.id,
        category=None,
        threshold=1,
        is_enabled=True,
    )
    assert isinstance(result, StickerChatEligibilityRuleDTO)

    updated_rule = db_session.query(TelegramChatStickerCollection).one()
    assert updated_rule.collection_id == another_sticker_collection.id
    assert updated_rule.character_id == another_sticker_character.id
    assert updated_rule.category is None
    assert updated_rule.threshold == 1
    assert updated_rule.is_enabled is True
    assert (
        updated_rule.group_id == telegram_chat_sticker_collection_rule.group_id
    ), "Group ID should not change."


@pytest.mark.asyncio
async def test_update_sticker_rule__set_character_null__pass(
    db_session: Session,
    mocked_managed_chat_action_factory: ChatManageActionFactory,
):
    telegram_chat_sticker_collection_rule = (
        TelegramChatStickerCollectionFactory.with_session(db_session).create()
    )

    requestor = UserFactory.create()
    another_sticker_collection = StickerCollectionFactory.create()

    action = mocked_managed_chat_action_factory(
        action_cls=TelegramChatStickerCollectionAction,
        db_session=db_session,
        chat_slug=telegram_chat_sticker_collection_rule.chat.slug,
        requestor=requestor,
    )

    existing_rule = db_session.query(TelegramChatStickerCollection).one()
    assert (
        existing_rule.collection_id
        == telegram_chat_sticker_collection_rule.collection_id
    )
    assert (
        existing_rule.character_id == telegram_chat_sticker_collection_rule.character_id
    )

    result = await action.update(
        rule_id=telegram_chat_sticker_collection_rule.id,
        collection_id=another_sticker_collection.id,
        character_id=None,
        category=None,
        threshold=1,
        is_enabled=True,
    )
    assert isinstance(result, StickerChatEligibilityRuleDTO)

    updated_rule = db_session.query(TelegramChatStickerCollection).one()
    assert updated_rule.collection_id == another_sticker_collection.id
    assert updated_rule.character_id is None
    assert (
        updated_rule.group_id == telegram_chat_sticker_collection_rule.group_id
    ), "Group ID should not change."
    assert updated_rule.is_enabled is True


@pytest.mark.asyncio
async def test_delete_sticker_rule__pass(
    db_session: Session,
    mocked_managed_chat_action_factory: ChatManageActionFactory,
) -> None:
    group = TelegramChatRuleGroupFactory.create()
    telegram_chat_sticker_collection_rule = (
        TelegramChatStickerCollectionFactory.with_session(db_session).create(
            group=group, chat=group.chat
        )
    )
    requestor = UserFactory.create()
    action = mocked_managed_chat_action_factory(
        action_cls=TelegramChatStickerCollectionAction,
        db_session=db_session,
        chat_slug=telegram_chat_sticker_collection_rule.chat.slug,
        requestor=requestor,
    )
    await action.delete(rule_id=telegram_chat_sticker_collection_rule.id)
    assert (
        db_session.query(TelegramChatStickerCollection).first() is None
    ), "The rule should be deleted."
    assert (
        db_session.query(TelegramChatRuleGroup).first() is None
    ), "The group should be deleted."
