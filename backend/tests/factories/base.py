from factory.alchemy import SQLAlchemyModelFactory


class BaseSQLAlchemyModelFactory(SQLAlchemyModelFactory):
    """Base factory for all SQLAlchemy models."""

    class Meta:
        abstract = True
        # This setting means the session will be used but the object won't be committed
        # until explicitly requested
        sqlalchemy_session_persistence = "flush"

    @classmethod
    def with_session(cls, session):
        """
        Return a factory class configured with the given session.

        Usage:
            factory_with_session = MyFactory.with_session(session)
            instance = factory_with_session.create()
        """

        class FactoryWithSession(cls):
            class Meta:
                model = cls._meta.model
                sqlalchemy_session = session
                sqlalchemy_session_persistence = (
                    cls._meta.sqlalchemy_session_persistence
                )

        return FactoryWithSession
