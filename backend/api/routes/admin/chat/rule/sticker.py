from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from starlette.requests import Request

from api.deps import get_db_session
from api.pos.chat import StickerChatEligibilityRuleFDO, TelegramChatStickerRuleCPO
from core.actions.chat.rule.sticker import TelegramChatStickerCollectionAction

manage_sticker_rules_router = APIRouter(prefix="/stickers")


@manage_sticker_rules_router.get("/{rule_id}")
async def get_chat_sticker_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> StickerChatEligibilityRuleFDO:
    action = TelegramChatStickerCollectionAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    rule = await action.read(rule_id=rule_id)
    return StickerChatEligibilityRuleFDO.model_validate(rule.model_dump())


@manage_sticker_rules_router.post("")
async def add_chat_sticker_rule(
    request: Request,
    slug: str,
    rule: TelegramChatStickerRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> StickerChatEligibilityRuleFDO:
    action = TelegramChatStickerCollectionAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    new_rule = await action.create(
        group_id=rule.group_id,
        collection_id=rule.collection_id,
        character_id=rule.character_id,
        category=rule.category,
        threshold=rule.expected,
    )
    return StickerChatEligibilityRuleFDO.model_validate(new_rule.model_dump())


@manage_sticker_rules_router.put("/{rule_id}")
async def update_chat_sticker_rule(
    request: Request,
    slug: str,
    rule_id: int,
    rule: TelegramChatStickerRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> StickerChatEligibilityRuleFDO:
    action = TelegramChatStickerCollectionAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    updated_rule = await action.update(
        rule_id=rule_id,
        collection_id=rule.collection_id,
        character_id=rule.character_id,
        category=rule.category,
        threshold=rule.expected,
        is_enabled=rule.is_enabled,
    )
    return StickerChatEligibilityRuleFDO.model_validate(updated_rule.model_dump())


@manage_sticker_rules_router.delete("/{rule_id}")
async def delete_chat_sticker_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> None:
    action = TelegramChatStickerCollectionAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    await action.delete(rule_id=rule_id)
