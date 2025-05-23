import asyncio

from celery.utils.log import get_task_logger

from core.actions.sticker import StickerCollectionAction
from core.constants import UPDATED_STICKERS_USER_IDS, CELERY_STICKER_FETCH_QUEUE_NAME
from core.services.db import DBService
from indexer.actions.sticker import IndexerStickerItemAction
from indexer.celery_app import app


logger = get_task_logger(__name__)


async def get_sticker_ownership_details():
    """
    Fetches sticker ownership details by retrieving collections and processing them to
    identify targeted user IDs, which are subsequently updated in the system.

    This function first retrieves all sticker collections from the database through a
    session. The collections are then processed to get a list of user IDs that require
    further attention. If any affected users are identified, their IDs are added to a
    redis-backed set for updates. If no affected users are identified, the system logs
    a message and skips further processing.

    :raises: Any exceptions raised during database access, collection retrieval, or
             processing will propagate to the caller.

    :return: None
    """
    with DBService().db_session() as db_session:
        collections_action = StickerCollectionAction(db_session=db_session)
        collections = collections_action.get_all()
        action = IndexerStickerItemAction(db_session)
        async for targeted_users_ids in action.refresh_ownerships(
            collections=collections
        ):
            if targeted_users_ids:
                logger.info(
                    f"Found {len(targeted_users_ids)} users that should be double-checked"
                )
                action.redis_service.add_to_set(
                    UPDATED_STICKERS_USER_IDS, *targeted_users_ids
                )


@app.task(
    name="fetch-sticker-ownership-details",
    queue=CELERY_STICKER_FETCH_QUEUE_NAME,
)
def fetch_sticker_ownership_details():
    asyncio.run(get_sticker_ownership_details())


async def refresh_sticker_collections():
    with DBService().db_session() as db_session:
        action = IndexerStickerItemAction(db_session)
        await action.refresh_collections()
        logger.info("Sticker collections refreshed.")


@app.task(
    name="fetch-sticker-collections",
    queue=CELERY_STICKER_FETCH_QUEUE_NAME,
)
def fetch_sticker_collections():
    asyncio.run(refresh_sticker_collections())
    app.send_task(
        "fetch-sticker-ownership-details",
        queue=CELERY_STICKER_FETCH_QUEUE_NAME,
    )
