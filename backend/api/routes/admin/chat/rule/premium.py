from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from api.deps import get_db_session
from api.pos.base import BaseExceptionFDO
from api.pos.chat import ChatEligibilityRuleFDO, TelegramChatPremiumRuleCPO
from core.actions.chat.rule.premium import TelegramChatPremiumAction

manage_premium_rules_router = APIRouter(prefix="/premium")


@manage_premium_rules_router.get(
    "/{rule_id}",
    responses={
        HTTP_200_OK: {"model": ChatEligibilityRuleFDO},
        HTTP_404_NOT_FOUND: {
            "description": "Rule Not Found",
            "model": BaseExceptionFDO,
        },
    },
)
async def get_premium_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> ChatEligibilityRuleFDO:
    action = TelegramChatPremiumAction(
        requestor=request.state.user,
        chat_slug=slug,
        db_session=db_session,
    )
    return ChatEligibilityRuleFDO.model_validate(
        action.read(rule_id=rule_id).model_dump()
    )


@manage_premium_rules_router.post(
    "",
    responses={
        HTTP_200_OK: {"model": ChatEligibilityRuleFDO},
        HTTP_400_BAD_REQUEST: {
            "description": "Occurs if Telegram Premium rule already exists for the chat",
            "model": BaseExceptionFDO,
        },
    },
)
async def add_premium_rule(
    request: Request,
    slug: str,
    group_id: int | None = None,
    db_session: Session = Depends(get_db_session),
) -> ChatEligibilityRuleFDO:
    action = TelegramChatPremiumAction(
        requestor=request.state.user,
        chat_slug=slug,
        db_session=db_session,
    )
    return ChatEligibilityRuleFDO.model_validate(
        action.create(group_id=group_id).model_dump()
    )


@manage_premium_rules_router.put(
    "/{rule_id}",
    responses={
        HTTP_200_OK: {"model": ChatEligibilityRuleFDO},
        HTTP_404_NOT_FOUND: {
            "description": "Rule Not Found",
            "model": BaseExceptionFDO,
        },
    },
)
async def update_premium_rule(
    request: Request,
    slug: str,
    rule_id: int,
    rule: TelegramChatPremiumRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> ChatEligibilityRuleFDO:
    action = TelegramChatPremiumAction(
        requestor=request.state.user,
        chat_slug=slug,
        db_session=db_session,
    )
    return ChatEligibilityRuleFDO.model_validate(
        action.update(rule_id=rule_id, is_enabled=rule.is_enabled).model_dump()
    )


@manage_premium_rules_router.delete(
    "/{rule_id}",
    responses={
        HTTP_200_OK: {"model": BaseExceptionFDO},
        HTTP_404_NOT_FOUND: {
            "description": "Rule Not Found",
            "model": BaseExceptionFDO,
        },
    },
)
async def delete_premium_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> None:
    action = TelegramChatPremiumAction(
        requestor=request.state.user,
        chat_slug=slug,
        db_session=db_session,
    )
    action.delete(rule_id=rule_id)
