import logging

from sqlalchemy import text

from api.pos.common import StatusFDO
from core.actions.base import BaseAction
from core.services.superredis import RedisService


logger = logging.getLogger(__name__)


class SystemAction(BaseAction):
    def healthcheck(self) -> StatusFDO:
        logger.debug("Checking database state")
        self.db_session.execute(text("SELECT 1"))
        logger.debug("DB state OK")
        logger.debug("Checking Redis state")
        redis_service = RedisService()
        redis_service.client.ping()
        logger.debug("Redis state OK")
        return StatusFDO(
            status="ok",
            message="Healthcheck OK",
        )
