from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from api.deps import get_db_session
from api.pos.base import BaseExceptionFDO
from api.pos.chat import TelegramChatEmojiRuleCPO, EmojiChatEligibilityRuleFDO
from core.actions.chat.rule.emoji import TelegramChatEmojiAction

manage_emoji_rules_router = APIRouter(prefix="/emoji")


@manage_emoji_rules_router.get(
    "/{rule_id}",
    responses={
        HTTP_200_OK: {"model": EmojiChatEligibilityRuleFDO},
        HTTP_404_NOT_FOUND: {
            "description": "Rule Not Found",
            "model": BaseExceptionFDO,
        },
    },
)
async def get_emoji_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> EmojiChatEligibilityRuleFDO:
    action = TelegramChatEmojiAction(
        requestor=request.state.user,
        chat_slug=slug,
        db_session=db_session,
    )
    return EmojiChatEligibilityRuleFDO.model_validate(
        action.read(rule_id=rule_id).model_dump()
    )


@manage_emoji_rules_router.post(
    "",
    responses={
        HTTP_200_OK: {"model": EmojiChatEligibilityRuleFDO},
        HTTP_400_BAD_REQUEST: {
            "description": "Occurs if Telegram Emoji rule already exists for the chat",
            "model": BaseExceptionFDO,
        },
    },
)
async def add_emoji_rule(
    request: Request,
    slug: str,
    rule: TelegramChatEmojiRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> EmojiChatEligibilityRuleFDO:
    action = TelegramChatEmojiAction(
        requestor=request.state.user,
        chat_slug=slug,
        db_session=db_session,
    )
    return EmojiChatEligibilityRuleFDO.model_validate(
        action.create(
            emoji_id=rule.emoji_id,
            group_id=rule.group_id,
        ).model_dump()
    )


@manage_emoji_rules_router.put(
    "/{rule_id}",
    responses={
        HTTP_200_OK: {"model": EmojiChatEligibilityRuleFDO},
        HTTP_404_NOT_FOUND: {
            "description": "Rule Not Found",
            "model": BaseExceptionFDO,
        },
    },
)
async def update_emoji_rule(
    request: Request,
    slug: str,
    rule_id: int,
    rule: TelegramChatEmojiRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> EmojiChatEligibilityRuleFDO:
    action = TelegramChatEmojiAction(
        requestor=request.state.user,
        chat_slug=slug,
        db_session=db_session,
    )
    return EmojiChatEligibilityRuleFDO.model_validate(
        action.update(
            rule_id=rule_id, emoji_id=rule.emoji_id, is_enabled=rule.is_enabled
        ).model_dump()
    )


@manage_emoji_rules_router.delete(
    "/{rule_id}",
    responses={
        HTTP_200_OK: {"model": BaseExceptionFDO},
        HTTP_404_NOT_FOUND: {
            "description": "Rule Not Found",
            "model": BaseExceptionFDO,
        },
    },
)
async def delete_emoji_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> None:
    action = TelegramChatEmojiAction(
        requestor=request.state.user,
        chat_slug=slug,
        db_session=db_session,
    )
    action.delete(rule_id=rule_id)
