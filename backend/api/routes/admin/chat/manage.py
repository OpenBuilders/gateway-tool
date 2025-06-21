from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from starlette.requests import Request

from api.deps import get_db_session
from api.pos.chat import (
    TelegramChatWithRulesFDO,
    TelegramChatFDO,
    EditChatCPO,
    ChatVisibilityCPO,
)
from api.routes.admin.chat.group import manage_rule_group_router
from api.routes.admin.chat.rule import manage_rules_router
from core.actions.chat import TelegramChatManageAction


admin_chat_manage_router = APIRouter(prefix="/{slug}", tags=["Chat management"])
admin_chat_manage_router.include_router(manage_rules_router)
admin_chat_manage_router.include_router(manage_rule_group_router)


@admin_chat_manage_router.get(
    "",
    description="Get specific chat details",
)
async def get_chat(
    request: Request,
    slug: str,
    db_session: Session = Depends(get_db_session),
) -> TelegramChatWithRulesFDO:
    telegram_chat_action = TelegramChatManageAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    result = await telegram_chat_action.get_with_eligibility_rules()
    return TelegramChatWithRulesFDO.from_dto(result)


@admin_chat_manage_router.put("")
async def update_chat(
    request: Request,
    slug: str,
    chat: EditChatCPO,
    db_session: Session = Depends(get_db_session),
) -> TelegramChatFDO:
    telegram_chat_action = TelegramChatManageAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    result = await telegram_chat_action.update(description=chat.description)
    return TelegramChatFDO.model_validate(result.model_dump())


@admin_chat_manage_router.delete(
    "",
    deprecated=True,
)
async def delete_chat(
    request: Request,
    slug: str,
    db_session: Session = Depends(get_db_session),
) -> None:
    telegram_chat_action = TelegramChatManageAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    await telegram_chat_action.delete()


@admin_chat_manage_router.put("/visibility")
async def update_chat_visibility(
    request: Request,
    slug: str,
    chat: ChatVisibilityCPO,
    db_session: Session = Depends(get_db_session),
) -> TelegramChatFDO:
    telegram_chat_action = TelegramChatManageAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    chat = await telegram_chat_action.update_visibility(chat.is_enabled)
    return TelegramChatFDO.model_validate(chat.model_dump())
