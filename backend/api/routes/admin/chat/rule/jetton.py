from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from starlette.requests import Request

from api.deps import get_db_session
from api.pos.chat import TelegramChatJettonRuleCPO, JettonEligibilityRuleFDO
from core.actions.chat.rule.blockchain import TelegramChatJettonAction


manage_jetton_rules_router = APIRouter(prefix="/jettons")


@manage_jetton_rules_router.get("/{rule_id}")
async def get_chat_jetton_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> JettonEligibilityRuleFDO:
    telegram_chat_jetton_action = TelegramChatJettonAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    return JettonEligibilityRuleFDO.model_validate(
        telegram_chat_jetton_action.read(rule_id=rule_id).model_dump()
    )


@manage_jetton_rules_router.post("")
async def add_chat_jetton_rule(
    request: Request,
    slug: str,
    rule: TelegramChatJettonRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> JettonEligibilityRuleFDO:
    telegram_chat_jetton_action = TelegramChatJettonAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    chat_jetton_rule = await telegram_chat_jetton_action.create(
        group_id=rule.group_id,
        category=rule.category,
        address_raw=rule.address,
        threshold=rule.expected,
    )
    return JettonEligibilityRuleFDO.model_validate(chat_jetton_rule.model_dump())


@manage_jetton_rules_router.put("/{rule_id}")
async def update_chat_jetton_rule(
    request: Request,
    slug: str,
    rule_id: int,
    rule: TelegramChatJettonRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> JettonEligibilityRuleFDO:
    action = TelegramChatJettonAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    chat_jetton_rule = await action.update(
        rule_id=rule_id,
        category=rule.category,
        address_raw=rule.address,
        threshold=rule.expected,
        is_enabled=rule.is_enabled,
    )
    return JettonEligibilityRuleFDO.model_validate(chat_jetton_rule.model_dump())


@manage_jetton_rules_router.delete("/{rule_id}")
async def delete_chat_jetton_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> None:
    action = TelegramChatJettonAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    await action.delete(rule_id=rule_id)
