import logging

from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from core.actions.base import BaseAction
from core.dtos.user import TelegramUserDTO
from core.models.user import User


logger = logging.getLogger(__name__)


class UserAction(BaseAction):
    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)

    def _initial_user_indexing(self, user: User) -> None:
        """
        Indexes the user's data upon their creation in the system. This method is
        intended for internal usage to initialize the indexing process for a user. It logs the
        process of indexing and ensures the data related to the user is properly
        indexed using internal and external service(-s).

        :param user: The user entity for which the data should be indexed.
        """
        logger.info(f"Indexing user {user.id!r} upon creation...")

    def create(self, telegram_user: TelegramUserDTO) -> User:
        """
        Creates a new user in the system based on the provided Telegram user data.

        This method takes in a Telegram user data transfer object (DTO) and creates
        a new user. It also performs an initial indexing of the created user.

        :param telegram_user: The DTO containing data of the Telegram user to
            be transformed into a system user.
        :return: The newly created user object.
        """
        user = self.user_service.create(telegram_user)
        self._initial_user_indexing(user)
        return user

    def create_or_update(self, telegram_user: TelegramUserDTO) -> User:
        """
        Creates or updates a user based on the provided Telegram user data. If a user with the given
        Telegram ID exists, their data is updated. Otherwise, a new user is created, and an initial
        indexing operation is performed on the new user.

        :param telegram_user: Data Transfer Object containing information about the Telegram user.
        :return: The updated or newly created user instance.
        """
        try:
            user = self.user_service.get_by_telegram_id(telegram_user.id)
            user = self.user_service.update(user, telegram_user)
        except NoResultFound:
            user = self.create(telegram_user)

        return user

    def get_or_create(self, telegram_user: TelegramUserDTO) -> User:
        """
        Retrieves an existing user by their Telegram ID or creates a new user if no such
        user exists. This function ensures that the user's data is either fetched
        from the database or initialized as a new entry. The retrieval or creation
        depends on the presence of a matching Telegram ID. Additionally, indexing
        is performed for newly created users to set up required infrastructure.

        :param telegram_user: An object containing Telegram user data necessary
            for either fetching or creating a User record.
        :return: The user object associated with the provided Telegram user data, either
            fetched from the database or newly created.
        """
        try:
            user = self.user_service.get_by_telegram_id(telegram_user.id)
        except NoResultFound:
            user = self.create(telegram_user)

        return user
