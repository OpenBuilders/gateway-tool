import asyncio

from celery.utils.log import get_task_logger

from community_manager.actions.chat import CommunityManagerChatAction
from community_manager.celery_app import app
from community_manager.settings import community_manager_settings
from core.actions.chat import TelegramChatAction
from core.actions.chat.rule.whitelist import (
    TelegramChatWhitelistExternalSourceContentAction,
)
from core.constants import (
    CELERY_SYSTEM_QUEUE_NAME,
)
from core.services.db import DBService

logger = get_task_logger(__name__)


@app.task(
    name="check-chat-members",
    queue=CELERY_SYSTEM_QUEUE_NAME,
)
def check_chat_members() -> None:
    if not community_manager_settings.enable_manager:
        logger.warning("Community manager is disabled.")
        return

    with DBService().db_session() as db_session:
        action = CommunityManagerChatAction(db_session=db_session)
        asyncio.run(action.sanity_chat_checks())


@app.task(
    name="refresh-chat-external-sources",
    queue=CELERY_SYSTEM_QUEUE_NAME,
    rate_limit="1/m",
)
def refresh_chat_external_sources() -> None:
    if not community_manager_settings.enable_manager:
        logger.warning("Community manager is disabled.")
        return

    with DBService().db_session() as db_session:
        action = TelegramChatWhitelistExternalSourceContentAction(db_session)
        # Celery tasks are not async, so we need to run the async function in a blocking way
        asyncio.run(action.refresh_enabled())
        logger.info("Chat external sources refreshed.")


async def refresh_all_chats_async() -> None:
    """
    Separate function to ensure that the telethon client is initiated in the same event loop
    """
    with DBService().db_session() as db_session:
        action = TelegramChatAction(db_session)
        await action.refresh_all()


@app.task(
    name="refresh-chats",
    queue=CELERY_SYSTEM_QUEUE_NAME,
)
def refresh_chats() -> None:
    if not community_manager_settings.enable_manager:
        logger.warning("Community manager is disabled.")
        return

    asyncio.run(refresh_all_chats_async())
    logger.info("Chats refreshed.")
