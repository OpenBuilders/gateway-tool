import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from ..db import Base, engine

logger = logging.getLogger(__name__)


class DBService:
    def __init__(self) -> None:
        pass

    @staticmethod
    def create_tables() -> None:
        logger.info("Creating tables...")
        Base.metadata.create_all(engine)

    @staticmethod
    def drop_tables() -> None:
        Base.metadata.drop_all(engine)

    @contextmanager
    def db_session(
        self,
    ) -> Generator[Session, None, None]:
        """See `DBSessionMaker.db_session` signature."""
        session = Session(bind=engine)
        try:
            yield session
            session.commit()
        except Exception as exc:
            logger.debug(
                f"Internal Error: {exc.__class__.__name__}. Rolling back session."
            )
            session.rollback()
            raise exc
        finally:
            session.close()
