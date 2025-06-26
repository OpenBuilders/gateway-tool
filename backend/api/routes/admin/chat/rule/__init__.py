from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.orm import Session
from starlette.requests import Request

from api.deps import get_db_session
from api.pos.chat import UpdateRuleGroupCPO
from api.pos.common import StatusFDO
from api.routes.admin.chat.rule.emoji import manage_emoji_rules_router
from api.routes.admin.chat.rule.gift import manage_gift_rules_router
from api.routes.admin.chat.rule.jetton import manage_jetton_rules_router
from api.routes.admin.chat.rule.nft import manage_nft_collection_rules_router
from api.routes.admin.chat.rule.premium import manage_premium_rules_router
from api.routes.admin.chat.rule.sticker import manage_sticker_rules_router
from api.routes.admin.chat.rule.toncoin import manage_toncoin_rules_router
from api.routes.admin.chat.rule.whitelist import (
    manage_whitelist_rules_router,
    manage_external_source_rules_router,
)
from core.actions.chat.rule import RuleAction

manage_rules_router = APIRouter(prefix="/rules", tags=["Chat Rules"])
manage_rules_router.include_router(manage_jetton_rules_router)
manage_rules_router.include_router(manage_nft_collection_rules_router)
manage_rules_router.include_router(manage_toncoin_rules_router)
manage_rules_router.include_router(manage_premium_rules_router)
manage_rules_router.include_router(manage_emoji_rules_router)
manage_rules_router.include_router(manage_sticker_rules_router)
manage_rules_router.include_router(manage_gift_rules_router)
manage_rules_router.include_router(manage_whitelist_rules_router)
manage_rules_router.include_router(manage_external_source_rules_router)


@manage_rules_router.put("/move", description="Move rule to another group")
async def move_rule(
    request: Request,
    slug: str,
    item: UpdateRuleGroupCPO,
    db_session: Session = Depends(get_db_session),
) -> StatusFDO:
    action = RuleAction(
        db_session=db_session, requestor=request.state.user, chat_slug=slug
    )
    action.move(item)
    return StatusFDO(
        status="success",
        message="Rule moved to another group successfully",
    )
