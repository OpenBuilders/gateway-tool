from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from starlette.requests import Request

from api.deps import get_db_session
from api.pos.chat import GiftChatEligibilityRuleFDO, TelegramChatGiftRuleCPO
from core.actions.chat.rule.gift import TelegramChatGiftCollectionAction

manage_gift_rules_router = APIRouter(prefix="/gifts")


@manage_gift_rules_router.get("/{rule_id}")
async def get_chat_gift_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> GiftChatEligibilityRuleFDO:
    action = TelegramChatGiftCollectionAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    rule = await action.read(rule_id=rule_id)
    return GiftChatEligibilityRuleFDO.model_validate(rule.model_dump())


@manage_gift_rules_router.post("")
async def add_chat_gift_rule(
    request: Request,
    slug: str,
    rule: TelegramChatGiftRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> GiftChatEligibilityRuleFDO:
    action = TelegramChatGiftCollectionAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    new_rule = await action.create(
        group_id=rule.group_id,
        collection_slug=rule.collection_slug,
        model=rule.model,
        backdrop=rule.backdrop,
        pattern=rule.pattern,
        category=rule.category,
        threshold=rule.expected,
    )
    return GiftChatEligibilityRuleFDO.model_validate(new_rule.model_dump())


@manage_gift_rules_router.put("/{rule_id}")
async def update_chat_gift_rule(
    request: Request,
    slug: str,
    rule_id: int,
    rule: TelegramChatGiftRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> GiftChatEligibilityRuleFDO:
    action = TelegramChatGiftCollectionAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    updated_rule = await action.update(
        rule_id=rule_id,
        collection_slug=rule.collection_slug,
        model=rule.model,
        backdrop=rule.backdrop,
        pattern=rule.pattern,
        category=rule.category,
        threshold=rule.expected,
        is_enabled=rule.is_enabled,
    )
    return GiftChatEligibilityRuleFDO.model_validate(updated_rule.model_dump())


@manage_gift_rules_router.delete("/{rule_id}")
async def delete_chat_gift_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> None:
    action = TelegramChatGiftCollectionAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    await action.delete(rule_id=rule_id)
