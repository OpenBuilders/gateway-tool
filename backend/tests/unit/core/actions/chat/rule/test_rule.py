import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.actions.chat.rule import RuleAction
from core.dtos.chat.rule import UpdateRuleGroupDTO
from core.enums.rule import EligibilityCheckType
from core.models.rule import (
    TelegramChatStickerCollection,
    TelegramChatPremium,
    TelegramChatEmoji,
    TelegramChatRuleGroup,
)
from tests.factories import UserFactory
from tests.factories.rule.emoji import TelegramChatEmojiRuleFactory
from tests.factories.rule.group import TelegramChatRuleGroupFactory
from tests.factories.rule.premium import TelegramChatPremiumFactory
from tests.factories.rule.sticker import TelegramChatStickerCollectionFactory
from tests.factories.rule.base import TelegramChatRuleBaseFactory
from tests.fixtures.action import ChatManageActionFactory


@pytest.mark.parametrize(
    ("factory_cls", "model", "rule_type"),
    [
        (
            TelegramChatStickerCollectionFactory,
            TelegramChatStickerCollection,
            EligibilityCheckType.STICKER_COLLECTION,
        ),
        # TODO remove these options as there is a constraint
        #  to have only one rule per chat for emoji and premium
        # (TelegramChatPremiumFactory, TelegramChatPremium, EligibilityCheckType.PREMIUM),
        # (TelegramChatEmojiRuleFactory, TelegramChatEmoji, EligibilityCheckType.EMOJI),
    ],
)
@pytest.mark.asyncio
async def test_move_rule__pass(
    db_session: Session,
    mocked_managed_chat_action_factory: ChatManageActionFactory,
    factory_cls: type[TelegramChatRuleBaseFactory],
    model: type[TelegramChatStickerCollection],
    rule_type: EligibilityCheckType,
) -> None:
    initial_group = TelegramChatRuleGroupFactory.create()
    rules = factory_cls.with_session(db_session).create_batch(
        size=3, group=initial_group, chat=initial_group.chat
    )
    target_rule = rules[0]

    requestor = UserFactory.create()
    another_group = TelegramChatRuleGroupFactory.create(chat=initial_group.chat)

    assert initial_group.id != another_group.id, "Groups should be different."

    action = mocked_managed_chat_action_factory(
        action_cls=RuleAction,
        db_session=db_session,
        chat_slug=target_rule.chat.slug,
        requestor=requestor,
    )

    existing_rules = db_session.query(model).all()
    for rule in existing_rules:
        assert (
            rule.group_id == target_rule.group_id
        ), "All rules should be in the same group."

    action.move(
        item=UpdateRuleGroupDTO(
            rule_id=target_rule.id,
            type=rule_type,
            group_id=another_group.id,
            order=0,
        )
    )

    updated_rules = db_session.query(model).all()
    for rule in updated_rules:
        assert rule.group_id == (
            another_group.id if rule.id == target_rule.id else initial_group.id
        ), "The rule should be moved to the new group."


@pytest.mark.parametrize(
    ("factory_cls", "model", "rule_type"),
    [
        (
            TelegramChatStickerCollectionFactory,
            TelegramChatStickerCollection,
            EligibilityCheckType.STICKER_COLLECTION,
        ),
        (TelegramChatPremiumFactory, TelegramChatPremium, EligibilityCheckType.PREMIUM),
        (TelegramChatEmojiRuleFactory, TelegramChatEmoji, EligibilityCheckType.EMOJI),
    ],
)
@pytest.mark.asyncio
async def test_move_rule__last_rule__group_removed(
    db_session: Session,
    mocked_managed_chat_action_factory: ChatManageActionFactory,
    factory_cls: type[TelegramChatRuleBaseFactory],
    model: type[TelegramChatStickerCollection],
    rule_type: EligibilityCheckType,
) -> None:
    initial_group = TelegramChatRuleGroupFactory.create()
    rule = factory_cls.with_session(db_session).create(
        group=initial_group, chat=initial_group.chat
    )

    requestor = UserFactory.create()
    another_group = TelegramChatRuleGroupFactory.create(chat=initial_group.chat)

    assert initial_group.id != another_group.id, "Groups should be different."

    action = mocked_managed_chat_action_factory(
        action_cls=RuleAction,
        db_session=db_session,
        chat_slug=rule.chat.slug,
        requestor=requestor,
    )
    action.move(
        item=UpdateRuleGroupDTO(
            rule_id=rule.id,
            type=rule_type,
            group_id=another_group.id,
            order=0,
        )
    )

    removed_group = (
        db_session.query(TelegramChatRuleGroup)
        .filter(TelegramChatRuleGroup.id == initial_group.id)
        .first()
    )
    assert removed_group is None, f"The group {initial_group.id} should be removed."

    updated_rule = db_session.query(model).one()

    assert (
        updated_rule.group_id == another_group.id
    ), "The rule should be moved to the new group."


@pytest.mark.parametrize(
    ("factory_cls", "model", "rule_type"),
    [
        (
            TelegramChatStickerCollectionFactory,
            TelegramChatStickerCollection,
            EligibilityCheckType.STICKER_COLLECTION,
        ),
        (TelegramChatPremiumFactory, TelegramChatPremium, EligibilityCheckType.PREMIUM),
        (TelegramChatEmojiRuleFactory, TelegramChatEmoji, EligibilityCheckType.EMOJI),
    ],
)
@pytest.mark.asyncio
async def test_move_rule__another_chat__fails(
    db_session: Session,
    mocked_managed_chat_action_factory: ChatManageActionFactory,
    factory_cls: type[TelegramChatRuleBaseFactory],
    model: type[TelegramChatStickerCollection],
    rule_type: EligibilityCheckType,
) -> None:
    initial_group = TelegramChatRuleGroupFactory.create()
    rule = factory_cls.with_session(db_session).create(
        group=initial_group, chat=initial_group.chat
    )

    another_group = TelegramChatRuleGroupFactory.create()
    requestor = UserFactory.create()

    action = mocked_managed_chat_action_factory(
        action_cls=RuleAction,
        db_session=db_session,
        chat_slug=rule.chat.slug,
        requestor=requestor,
    )
    with pytest.raises(HTTPException) as exc_info:
        action.move(
            item=UpdateRuleGroupDTO(
                rule_id=rule.id,
                type=rule_type,
                group_id=another_group.id,
                order=0,
            )
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_move_rule__group_not_found__fails(
    db_session: Session,
    mocked_managed_chat_action_factory: ChatManageActionFactory,
) -> None:
    initial_group = TelegramChatRuleGroupFactory.create()
    rule = TelegramChatStickerCollectionFactory.with_session(db_session).create(
        group=initial_group, chat=initial_group.chat
    )
    requestor = UserFactory.create()

    action = mocked_managed_chat_action_factory(
        action_cls=RuleAction,
        db_session=db_session,
        chat_slug=rule.chat.slug,
        requestor=requestor,
    )
    with pytest.raises(HTTPException) as exc_info:
        action.move(
            item=UpdateRuleGroupDTO(
                rule_id=rule.id,
                type=EligibilityCheckType.STICKER_COLLECTION,
                group_id=888,
                order=None,
            )
        )

    assert exc_info.value.status_code == 400
