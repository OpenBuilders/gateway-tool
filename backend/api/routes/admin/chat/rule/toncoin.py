from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from starlette.requests import Request

from api.deps import get_db_session
from api.pos.chat import TelegramChatToncoinRuleCPO, ToncoinEligibilityRuleFDO
from core.actions.chat.rule.blockchain import TelegramChatToncoinAction


manage_toncoin_rules_router = APIRouter(prefix="/toncoin")


@manage_toncoin_rules_router.get("/{rule_id}")
async def get_chat_toncoin_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> ToncoinEligibilityRuleFDO:
    telegram_chat_toncoin_action = TelegramChatToncoinAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    return ToncoinEligibilityRuleFDO.model_validate(
        telegram_chat_toncoin_action.read(rule_id=rule_id).model_dump()
    )


@manage_toncoin_rules_router.post("")
async def add_chat_toncoin_rule(
    request: Request,
    slug: str,
    rule: TelegramChatToncoinRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> ToncoinEligibilityRuleFDO:
    telegram_chat_toncoin_action = TelegramChatToncoinAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    return ToncoinEligibilityRuleFDO.model_validate(
        telegram_chat_toncoin_action.create(
            group_id=rule.group_id,
            category=rule.category,
            threshold=rule.expected,
        ).model_dump()
    )


@manage_toncoin_rules_router.put("/{rule_id}")
async def update_chat_toncoin_rule(
    request: Request,
    slug: str,
    rule_id: int,
    rule: TelegramChatToncoinRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> ToncoinEligibilityRuleFDO:
    telegram_chat_toncoin_action = TelegramChatToncoinAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    return ToncoinEligibilityRuleFDO.model_validate(
        telegram_chat_toncoin_action.update(
            rule_id=rule_id,
            category=rule.category,
            threshold=rule.expected,
            is_enabled=rule.is_enabled,
        ).model_dump()
    )


@manage_toncoin_rules_router.delete("/{rule_id}")
async def delete_chat_toncoin_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> None:
    telegram_chat_toncoin_action = TelegramChatToncoinAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    telegram_chat_toncoin_action.delete(rule_id=rule_id)
