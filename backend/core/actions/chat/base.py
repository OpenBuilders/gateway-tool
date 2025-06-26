import logging

from fastapi import HTTPException
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy.orm import Session
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from core.actions.base import BaseAction
from core.exceptions.rule import TelegramChatRuleNotFound
from core.models.user import User
from core.models.chat import TelegramChat
from core.services.chat import TelegramChatService
from core.services.chat.rule.group import TelegramChatRuleGroupService
from core.services.chat.user import TelegramChatUserService


logger = logging.getLogger(__name__)


class ManagedChatBaseAction(BaseAction):
    _chat: TelegramChat
    is_admin_action: bool = True

    def __init__(
        self, db_session: Session, requestor: User, chat_slug: str, **kwargs
    ) -> None:
        super().__init__(db_session)
        self.telegram_chat_service = TelegramChatService(db_session)
        self.telegram_chat_user_service = TelegramChatUserService(db_session)
        self.telegram_chat_rule_group_service = TelegramChatRuleGroupService(db_session)

        self._chat = self.__get_target_chat(requestor=requestor, chat_slug=chat_slug)

    def __get_target_chat(self, requestor: User, chat_slug: str) -> TelegramChat:
        """
        Retrieves a target chat based on the given requestor and chat slug. It attempts
        to fetch the chat using the `telegram_chat_service`. If the chat is not found, an exception
        is raised. If the action requires administrative permission, it checks whether the requestor
        is an admin of the chat using the `telegram_chat_user_service`.

        :param requestor: User object that makes the request
        :param chat_slug: Unique slug identifier for the target chat
        :return: The target TelegramChat object
        :raises HTTPException: If the chat is not found or if the requestor lacks admin permissions
        """
        try:
            chat = self.telegram_chat_service.get_by_slug(chat_slug)
        except NoResultFound:
            logger.debug(f"Chat with slug {chat_slug!r} not found")
            raise HTTPException(
                detail="Chat not found",
                status_code=HTTP_404_NOT_FOUND,
            )

        if self.is_admin_action:
            if not self.telegram_chat_user_service.is_chat_admin(
                chat_id=chat.id, user_id=requestor.id
            ):
                raise HTTPException(
                    detail="Forbidden",
                    status_code=HTTP_403_FORBIDDEN,
                )

        return chat

    @property
    def chat(self) -> TelegramChat:
        return self._chat

    def resolve_group_id(self, group_id: int | None) -> int:
        """
        Resolves the group ID for a given chat ID. If the `group_id` is provided and
        exists for the given `chat_id`, it is returned.
        If the `group_id` is not provided or does not exist, a new group is created for the chat,
        and its ID is returned.

        :param group_id: Unique identifier for the group, or None if a new group
            is to be created.
        :return: Resolved or newly created group ID.
        :raises TelegramChatRuleNotFound: If the specified `group_id` does not
            exist for the given `chat_id`.
        """
        if group_id is not None:
            try:
                self.telegram_chat_rule_group_service.get(
                    chat_id=self.chat.id, group_id=group_id
                )
                return group_id
            except NoResultFound as e:
                raise TelegramChatRuleNotFound(
                    f"No group with ID {group_id!r} found for chat {self.chat.id!r}."
                ) from e

        new_group = self.telegram_chat_rule_group_service.create(chat_id=self.chat.id)
        return new_group.id

    def remove_group_if_empty(self, group_id: int) -> None:
        """
        Removes a group by its ID if the group is empty. If the group contains any
        data or associations, it will not be removed, and a debug message logs
        this condition. This function performs a deletion operation and handles
        database integrity exceptions.

        :param group_id: An integer representing the unique identifier of the group
            to be removed.
        """
        try:
            group_removed = self.telegram_chat_rule_group_service.delete(
                chat_id=self.chat.id, group_id=group_id
            )
            if group_removed:
                logger.info(
                    f"Deleted rule group {group_id!r} for chat {self.chat.id!r} as it had no rules left."
                )
            else:
                logger.warning(
                    f"Group {group_id!r} was not deleted as it was not found."
                )
        except IntegrityError:
            self.db_session.rollback()
            logger.debug(f"Group {group_id!r} is not empty")

        return None
