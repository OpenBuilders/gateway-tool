from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from starlette.requests import Request

from api.deps import get_db_session
from api.pos.chat import NftEligibilityRuleFDO, TelegramChatNFTCollectionRuleCPO
from core.actions.chat.rule.blockchain import TelegramChatNFTCollectionAction


manage_nft_collection_rules_router = APIRouter(prefix="/nft-collections")


@manage_nft_collection_rules_router.get("/{rule_id}")
async def get_chat_nft_collection_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> NftEligibilityRuleFDO:
    action = TelegramChatNFTCollectionAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    return NftEligibilityRuleFDO.model_validate(
        action.read(rule_id=rule_id).model_dump()
    )


@manage_nft_collection_rules_router.post("")
async def add_chat_nft_collection_rule(
    request: Request,
    slug: str,
    rule: TelegramChatNFTCollectionRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> NftEligibilityRuleFDO:
    action = TelegramChatNFTCollectionAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    chat_nft_collection_rule = await action.create(
        group_id=rule.group_id,
        address_raw=rule.address,
        threshold=rule.expected,
        category=rule.category,
        asset=rule.asset,
    )
    return NftEligibilityRuleFDO.model_validate(chat_nft_collection_rule.model_dump())


@manage_nft_collection_rules_router.put("/{rule_id}")
async def update_chat_nft_collection_rule(
    request: Request,
    slug: str,
    rule_id: int,
    rule: TelegramChatNFTCollectionRuleCPO,
    db_session: Session = Depends(get_db_session),
) -> NftEligibilityRuleFDO:
    action = TelegramChatNFTCollectionAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    nft_collection_rule = await action.update(
        rule_id=rule_id,
        asset=rule.asset,
        address_raw=rule.address,
        category=rule.category,
        threshold=rule.expected,
        is_enabled=rule.is_enabled,
    )
    return NftEligibilityRuleFDO.model_validate(nft_collection_rule.model_dump())


@manage_nft_collection_rules_router.delete("/{rule_id}")
async def delete_chat_nft_collection_rule(
    request: Request,
    slug: str,
    rule_id: int,
    db_session: Session = Depends(get_db_session),
) -> None:
    action = TelegramChatNFTCollectionAction(
        db_session=db_session,
        requestor=request.state.user,
        chat_slug=slug,
    )
    await action.delete(rule_id=rule_id)
