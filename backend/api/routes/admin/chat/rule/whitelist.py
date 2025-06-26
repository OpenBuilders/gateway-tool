import logging

from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.status import HTTP_400_BAD_REQUEST

from api.deps import get_db_session
from api.pos.chat import (
    CreateWhitelistRuleCPO,
    WhitelistRuleFDO,
    UpdateWhitelistRuleCPO,
    CreateWhitelistRuleExternalCPO,
    WhitelistRuleExternalFDO,
    UpdateWhitelistRuleExternalCPO,
)
from core.actions.chat.rule.whitelist import (
    TelegramChatWhitelistAction,
    TelegramChatWhitelistExternalSourceAction,
)
from core.exceptions.chat import TelegramChatInvalidExternalSourceError
from core.exceptions.rule import TelegramChatRuleExists

logger = logging.getLogger(__name__)
manage_whitelist_rules_router = admin_chat_router = APIRouter(prefix="/whitelist")


@manage_whitelist_rules_router.post("")
async def add_chat_whitelist_rule(
    request: Request,
    slug: str,
    rule: CreateWhitelistRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> WhitelistRuleFDO:
    action = TelegramChatWhitelistAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    new_rule = action.create(
        group_id=rule.group_id,
        name=rule.name,
        description=rule.description,
    )
    result = await action.set_content(
        rule_id=new_rule.id,
        content=rule.users,
    )
    return WhitelistRuleFDO.model_validate(result.model_dump())


@manage_whitelist_rules_router.put("/{rule_id}")
async def update_chat_whitelist_rule(
    request: Request,
    slug: str,
    rule_id: int,
    rule: UpdateWhitelistRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> WhitelistRuleFDO:
    action = TelegramChatWhitelistAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    action.update(
        rule_id=rule_id,
        name=rule.name,
        description=rule.description,
        is_enabled=rule.is_enabled,
    )
    result = await action.set_content(rule_id=rule_id, content=rule.users)
    return WhitelistRuleFDO.model_validate(result.model_dump())


@manage_whitelist_rules_router.delete("/{rule_id}")
async def delete_chat_whitelist_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> None:
    action = TelegramChatWhitelistAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    await action.delete(rule_id=rule_id)


@manage_whitelist_rules_router.get("/{rule_id}")
async def get_chat_whitelist_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> WhitelistRuleFDO:
    action = TelegramChatWhitelistAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    result = action.get(
        rule_id=rule_id,
    )
    return WhitelistRuleFDO.model_validate(result.model_dump())


manage_external_source_rules_router = APIRouter(prefix="/external-source")


@manage_external_source_rules_router.post("")
async def add_chat_whitelist_external_source_rule(
    request: Request,
    slug: str,
    rule: CreateWhitelistRuleExternalCPO,
    db_session: Session = Depends(get_db_session),
) -> WhitelistRuleExternalFDO:
    action = TelegramChatWhitelistExternalSourceAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    try:
        new_rule = await action.create(
            group_id=rule.group_id,
            name=rule.name,
            description=rule.description,
            external_source_url=str(rule.url),
            auth_key=rule.auth_key,
            auth_value=rule.auth_value,
        )
    except TelegramChatRuleExists:
        raise HTTPException(
            detail="External source rule already exists",
            status_code=HTTP_400_BAD_REQUEST,
        )
    except TelegramChatInvalidExternalSourceError:
        raise HTTPException(
            detail="Invalid external source URL",
            status_code=HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error("Failed to create whitelist external source", exc_info=e)
        raise HTTPException(
            detail="Failed to create whitelist external source",
            status_code=HTTP_400_BAD_REQUEST,
        )
    return WhitelistRuleExternalFDO.model_validate(new_rule.model_dump())


@manage_external_source_rules_router.get("/{rule_id}")
async def get_chat_whitelist_external_source_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> WhitelistRuleExternalFDO:
    action = TelegramChatWhitelistExternalSourceAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    result = action.get(rule_id=rule_id)
    return WhitelistRuleExternalFDO.model_validate(result.model_dump())


@manage_external_source_rules_router.put("/{rule_id}")
async def update_chat_whitelist_external_source_rule(
    request: Request,
    slug: str,
    rule_id: int,
    rule: UpdateWhitelistRuleExternalCPO,
    db_session: Session = Depends(get_db_session),
) -> WhitelistRuleExternalFDO:
    action = TelegramChatWhitelistExternalSourceAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    try:
        await action.update(
            rule_id=rule_id,
            name=rule.name,
            description=rule.description,
            external_source_url=str(rule.url),
            auth_key=rule.auth_key,
            auth_value=rule.auth_value,
            is_enabled=rule.is_enabled,
        )
    except Exception as e:
        logger.error("Failed to update whitelist external source", exc_info=e)
        raise HTTPException(
            detail="Failed to update whitelist external source",
            status_code=HTTP_400_BAD_REQUEST,
        )

    result = action.get(rule_id=rule_id)
    return WhitelistRuleExternalFDO.model_validate(result.model_dump())


@manage_external_source_rules_router.delete("/{rule_id}")
async def delete_chat_whitelist_external_source_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> None:
    action = TelegramChatWhitelistExternalSourceAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    await action.delete(rule_id=rule_id)
