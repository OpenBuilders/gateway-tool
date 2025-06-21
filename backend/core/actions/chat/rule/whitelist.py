import logging

from fastapi import HTTPException
from httpx import HTTPError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.status import HTTP_404_NOT_FOUND

from core.actions.authorization import AuthorizationAction
from core.actions.base import BaseAction
from core.actions.chat.base import ManagedChatBaseAction
from core.dtos.chat.rule.whitelist import (
    WhitelistRuleItemsDifferenceDTO,
    WhitelistRuleDTO,
    WhitelistRuleExternalDTO,
    CreateTelegramChatWhitelistExternalSourceDTO,
    UpdateTelegramChatWhitelistExternalSourceDTO,
    CreateTelegramChatWhitelistDTO,
    UpdateTelegramChatWhitelistDTO,
)
from core.exceptions.rule import TelegramChatRuleExists
from core.models.rule import TelegramChatWhitelistExternalSource
from core.models.user import User
from core.services.chat.rule.whitelist import (
    TelegramChatExternalSourceService,
    TelegramChatWhitelistService,
)
from core.services.chat.user import TelegramChatUserService
from core.utils.external_source import fetch_dynamic_allowed_members
from core.exceptions.chat import (
    TelegramChatInvalidExternalSourceError,
)

logger = logging.getLogger(__name__)


class TelegramChatWhitelistExternalSourceContentAction(BaseAction):
    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)
        self.telegram_chat_external_source_service = TelegramChatExternalSourceService(
            db_session
        )
        self.telegram_chat_user_service = TelegramChatUserService(db_session)

    def _set_content(
        self, rule: TelegramChatWhitelistExternalSource, content: list[int]
    ) -> WhitelistRuleExternalDTO:
        external_source = self.telegram_chat_external_source_service.set_content(
            rule=rule, content=content
        )
        logger.info(f"External source {rule.id!r} updated successfully")
        return WhitelistRuleExternalDTO.from_orm(external_source)

    async def refresh_external_source(
        self,
        source: TelegramChatWhitelistExternalSource,
        raise_for_error: bool = False,
    ) -> None:
        """
        Refreshes an external source for a Telegram chat dynamic list.

        This method fetches the dynamic list members from a given external source URL,
        updates the internal data store to reflect the changes in the list, and
        handles the removal of chat members who are no longer eligible. It supports
        raising exceptions for errors encountered during the process, as controlled by
        the `raise_for_error` parameter.

        :param source: The external source from which the dynamic list of members should be
            fetched. Represents the source URL and its current content.
        :param raise_for_error: A boolean flag to indicate whether exceptions should be
            raised when errors occur during the fetch operation. Defaults to False.
        :return: This asynchronous method does not return a value.

        :raises TelegramChatInvalidExternalSourceError: If the external source is invalid.
        """
        try:
            result = await fetch_dynamic_allowed_members(
                source.url,
                auth_key=source.auth_key,
                auth_value=source.auth_value,
            )
        except HTTPError as e:
            logger.warning(f"Failed to fetch external source {source.url!r}: {e}")
            if raise_for_error:
                raise
            return
        except TelegramChatInvalidExternalSourceError as e:
            logger.warning(f"Invalid external source {source.url!r}: {e}")
            if raise_for_error:
                raise
            return
        except Exception as e:
            logger.exception(f"Failed to fetch external source {source.url!r}: {e}")
            if raise_for_error:
                raise
            return

        difference = WhitelistRuleItemsDifferenceDTO(
            previous=source.content,
            current=result.users,
        )

        self._set_content(rule=source, content=result.users)

        chat_members = self.telegram_chat_user_service.get_all(
            user_ids=difference.removed
        )
        authorization_action = AuthorizationAction(self.db_session)
        await authorization_action.kick_ineligible_chat_members(
            chat_members=chat_members
        )

        logger.info(f"Refreshed external source {source.url!r} successfully")

    async def refresh_enabled(self, raise_for_error: bool = False) -> None:
        sources = self.telegram_chat_external_source_service.get_all(enabled_only=True)
        for source in sources:
            await self.refresh_external_source(source, raise_for_error=raise_for_error)


class TelegramChatWhitelistExternalSourceAction(ManagedChatBaseAction):
    def __init__(self, db_session: Session, requestor: User, chat_slug: str) -> None:
        super().__init__(
            db_session=db_session, requestor=requestor, chat_slug=chat_slug
        )
        self.telegram_chat_external_source_service = TelegramChatExternalSourceService(
            db_session
        )
        self.content_action = TelegramChatWhitelistExternalSourceContentAction(
            db_session
        )

    def get(self, rule_id: int) -> WhitelistRuleExternalDTO:
        external_source = self.telegram_chat_external_source_service.get(
            chat_id=self.chat.id, id_=rule_id
        )
        return WhitelistRuleExternalDTO.from_orm(external_source)

    async def create(
        self,
        group_id: int | None,
        external_source_url: str,
        name: str,
        description: str | None,
        auth_key: str | None,
        auth_value: str | None,
    ) -> WhitelistRuleExternalDTO:
        """
        Creates a new external source for a chat and validates it. If validation fails, rolls
        back the database transaction.

        :param group_id: The identifier of the group to which the external source belongs.
        :param external_source_url: The URL of the external source to be added.
        :param name: The name of the external source.
        :param description: An optional description of the external source.
        :param auth_key: An authentication key for the external source.
        :param auth_value: An authentication value for the external source.
        :return: An instance of WhitelistRuleExternalDTO representing the created external source.

        :raises TelegramChatInvalidExternalSourceError: If the external source is invalid.
        """
        group_id = self.resolve_group_id(chat_id=self.chat.id, group_id=group_id)

        try:
            external_source = self.telegram_chat_external_source_service.create(
                CreateTelegramChatWhitelistExternalSourceDTO(
                    chat_id=self.chat.id,
                    group_id=group_id,
                    external_source_url=external_source_url,
                    name=name,
                    description=description,
                    auth_key=auth_key,
                    auth_value=auth_value,
                    is_enabled=True,
                ),
            )
        except IntegrityError as e:
            message = f"External source rule already exists for chat {self.chat.id!r} with url {external_source_url!r}. "
            logger.warning(message, exc_info=e)
            raise TelegramChatRuleExists(message) from e
        try:
            await self.content_action.refresh_external_source(
                source=external_source, raise_for_error=True
            )
        except Exception as e:
            logger.warning(
                "Rolling back transaction as an error occurred while validating the source"
            )
            self.db_session.rollback()
            raise e

        logger.info(f"External source {external_source.id!r} created successfully")
        # No need for a manual commit, as it's already done in the service during set_content
        return WhitelistRuleExternalDTO.from_orm(external_source)

    async def update(
        self,
        rule_id: int,
        external_source_url: str,
        name: str,
        description: str | None,
        auth_key: str | None,
        auth_value: str | None,
        is_enabled: bool,
    ) -> WhitelistRuleExternalDTO:
        """
        Updates an external source for a given chat rule. This method updates the external
        source details such as the URL, name, description, and enables or disables the source
        based on the provided parameters. Additionally, it commits changes or rolls back the
        transaction if an error occurs during the validation of the source.

        :param rule_id: The unique identifier of the rule being updated.
        :param external_source_url: The URL of the external source to be updated.
        :param name: The name of the external source being updated.
        :param description: An optional description of the external source.
        :param auth_key: An authentication key for the external source.
        :param auth_value: An authentication value for the external source.
        :param is_enabled: A flag indicating whether the external source should be enabled or
            disabled.
        :return: An instance of `WhitelistRuleExternalDTO` containing the updated external
            source details.

        :raises TelegramChatInvalidExternalSourceError: If the external source is invalid.
        """
        try:
            rule = self.telegram_chat_external_source_service.get(
                chat_id=self.chat.id, id_=rule_id
            )
        except IntegrityError as e:
            message = f"External source rule {rule_id!r} does not exist for chat {self.chat.id!r}. "
            logger.warning(message, exc_info=e)
            raise HTTPException(detail=message, status_code=HTTP_404_NOT_FOUND) from e

        external_source = self.telegram_chat_external_source_service.update(
            rule=rule,
            dto=UpdateTelegramChatWhitelistExternalSourceDTO(
                external_source_url=external_source_url,
                name=name,
                description=description,
                auth_key=auth_key,
                auth_value=auth_value,
                is_enabled=is_enabled,
            ),
        )
        if is_enabled:
            # No need for a manual commit, as it's already done in the service during set_content
            try:
                await self.content_action.refresh_external_source(
                    source=external_source, raise_for_error=True
                )
            except Exception as e:
                logger.warning(
                    "Rolling back transaction as an error occurred while validating the source"
                )
                self.db_session.rollback()
                raise e
        else:
            self.db_session.commit()

        logger.info(f"External source {rule_id!r} updated successfully")
        return WhitelistRuleExternalDTO.from_orm(external_source)

    async def delete(self, rule_id: int) -> None:
        self.telegram_chat_external_source_service.delete(
            chat_id=self.chat.id, rule_id=rule_id
        )
        logger.info(f"External source {rule_id!r} deleted successfully")


class TelegramChatWhitelistAction(ManagedChatBaseAction):
    def __init__(self, db_session: Session, requestor: User, chat_slug: str) -> None:
        super().__init__(
            db_session=db_session,
            requestor=requestor,
            chat_slug=chat_slug,
        )
        self.telegram_chat_whitelist_service = TelegramChatWhitelistService(db_session)

    def get(self, rule_id: int) -> WhitelistRuleDTO:
        whitelist = self.telegram_chat_whitelist_service.get(
            chat_id=self.chat.id, id_=rule_id
        )
        return WhitelistRuleDTO.from_orm(whitelist)

    def create(
        self, group_id: int | None, name: str, description: str | None = None
    ) -> WhitelistRuleDTO:
        group_id = self.resolve_group_id(chat_id=self.chat.id, group_id=group_id)

        whitelist = self.telegram_chat_whitelist_service.create(
            CreateTelegramChatWhitelistDTO(
                group_id=group_id,
                name=name,
                description=description,
                is_enabled=True,
                chat_id=self.chat.id,
            ),
        )
        logger.info(f"Whitelist {whitelist.id!r} created successfully")
        return WhitelistRuleDTO.from_orm(whitelist)

    def update(
        self, rule_id: int, name: str, description: str | None, is_enabled: bool
    ) -> WhitelistRuleDTO:
        try:
            rule = self.telegram_chat_whitelist_service.get(
                chat_id=self.chat.id, id_=rule_id
            )
        except IntegrityError as e:
            message = (
                f"Whitelist rule {rule_id!r} does not exist for chat {self.chat.id!r}. "
            )
            logger.warning(message, exc_info=e)
            raise HTTPException(detail=message, status_code=HTTP_404_NOT_FOUND) from e

        whitelist = self.telegram_chat_whitelist_service.update(
            rule=rule,
            dto=UpdateTelegramChatWhitelistDTO(
                name=name,
                description=description,
                is_enabled=is_enabled,
            ),
        )
        logger.info(f"Whitelist {rule_id!r} updated successfully")
        return WhitelistRuleDTO.from_orm(whitelist)

    async def set_content(self, rule_id: int, content: list[int]) -> WhitelistRuleDTO:
        """
        Sets the content of a whitelist rule for a specified chat and handles any actions
        related to changes in the list that may impact chat members.

        This method allows modifying the content of the specified whitelist rule using the
        provided list of integers. It validates the changes, updates the rule, computes the
        difference before and after the update, and performs necessary actions on members
        who no longer meet the eligibility criteria due to the changes. Finally, it logs the
        success of the operation and returns an updated representation of the whitelist rule.

        :param rule_id: An integer identifying the rule to be updated within the whitelist
            associated with the specified chat. Determines which rule should have its
            content modified.
        :param content: A list of integers representing the new content to be associated
            with the specified whitelist rule. Applies the changes to this content while
            analyzing the difference from the existing data.
        :return: An instance of `WhitelistRuleDTO`, which is a data transfer object that
            encapsulates the updated state of the whitelist rule after the operation
            has been successfully executed.
        """
        rule = self.telegram_chat_whitelist_service.get(
            chat_id=self.chat.id, id_=rule_id
        )
        whitelist = self.telegram_chat_whitelist_service.set_content(
            rule=rule, content=content
        )
        difference = WhitelistRuleItemsDifferenceDTO(
            previous=rule.content,
            current=content,
        )

        if difference.removed:
            chat_members = self.telegram_chat_user_service.get_all(
                user_ids=difference.removed
            )
            authorization_action = AuthorizationAction(self.db_session)
            await authorization_action.kick_ineligible_chat_members(
                chat_members=chat_members
            )

        logger.info(f"Whitelist {rule_id!r} updated successfully")
        return WhitelistRuleDTO.from_orm(whitelist)

    async def delete(self, rule_id: int) -> None:
        self.telegram_chat_whitelist_service.delete(
            chat_id=self.chat.id,
            rule_id=rule_id,
        )
        logger.info(f"Whitelist {rule_id!r} deleted successfully")
