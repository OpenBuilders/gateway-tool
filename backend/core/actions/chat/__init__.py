import logging
from pathlib import Path

import sqlalchemy
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from telethon import TelegramClient
from telethon.errors import BadRequestError
from telethon.utils import get_peer_id

from core.actions.chat.base import ManagedChatBaseAction
from core.constants import REQUIRED_BOT_PRIVILEGES
from core.dtos.chat import (
    BaseTelegramChatDTO,
    TelegramChatDTO,
)
from core.dtos.chat.rules import (
    TelegramChatWithRulesDTO,
    EligibilityCheckType,
)
from core.dtos.chat.rules.summary import (
    RuleEligibilitySummaryDTO,
    TelegramChatWithEligibilitySummaryDTO,
)
from core.actions.authorization import AuthorizationAction
from core.actions.base import BaseAction
from core.dtos.chat.rules.nft import NftEligibilityRuleDTO, NftRuleEligibilitySummaryDTO
from core.exceptions.chat import (
    TelegramChatNotSufficientPrivileges,
    TelegramChatAlreadyExists,
    TelegramChatNotExists,
)
from core.dtos.user import TelegramUserDTO
from core.models.chat import TelegramChat
from core.models.user import User
from core.services.cdn import CDNService
from core.services.chat import TelegramChatService
from core.services.chat.user import TelegramChatUserService
from core.services.supertelethon import TelethonService, ChatPeerType
from core.services.user import UserService
from core.settings import core_settings


logger = logging.getLogger(__name__)


class TelegramChatAction(BaseAction):
    def __init__(
        self, db_session: Session, telethon_client: TelegramClient | None = None
    ):
        logger.info(f"Initializing TelegramChatAction {telethon_client=}")
        super().__init__(db_session)
        self.telegram_chat_service = TelegramChatService(db_session)
        self.telegram_chat_user_service = TelegramChatUserService(db_session)
        self.authorization_action = AuthorizationAction(db_session)
        self.telethon_service = TelethonService(client=telethon_client)
        self.cdn_service = CDNService()

    def get_all(self, requestor: User) -> list[BaseTelegramChatDTO]:
        """
        Fetches all Telegram chats accessible to the requesting user.

        If the requestor has administrative privileges, the method retrieves all
        Telegram chats. If the requestor does not have administrative privileges,
        only the chats managed by the requestor are retrieved. The data is then
        converted to a list of BaseTelegramChatDTO objects.

        :param requestor: The user making the request.

        :return: A list of BaseTelegramChatDTO objects representing the chats
            accessible to the requestor.
        """
        if requestor.is_admin:
            chats = self.telegram_chat_service.get_all()
        else:
            chats = self.telegram_chat_service.get_all_managed(user_id=requestor.id)

        return [BaseTelegramChatDTO.from_orm(chat) for chat in chats]

    async def _get_chat_data(
        self,
        chat_identifier: str | int,
    ) -> ChatPeerType:
        """
        Retrieves the chat data associated with the provided chat identifier.

        This method interacts with the Telethon service to fetch chat information
        and validate the bot's administrative privileges within the chat. If the
        specified chat is not found or the bot does not have sufficient privileges
        to manage the chat, appropriate exceptions are raised.

        :param chat_identifier: The unique identifier of the chat, which could be
            either a string (e.g., username or chat name) or an integer (e.g.,
            chat ID). Preferably, this should be an ID as it reduces the number
            of requests to the Telegram API.
        :return: An instance of ChatPeerType representing the retrieved chat data.
        :raises TelegramChatNotExists: If the specified chat is not found in
            Telegram.
        :raises TelegramChatNotSufficientPrivileges: If the bot lacks the required
            administrative privileges to manage the chat.
        """
        await self.telethon_service.start()
        try:
            chat = await self.telethon_service.get_chat(chat_identifier)
        except (ValueError, BadRequestError) as e:
            logger.exception(f"Chat {chat_identifier!r} not found", exc_info=e)
            raise TelegramChatNotExists(f"Chat {chat_identifier!r} not found")

        if not chat.admin_rights or not all(
            [getattr(chat.admin_rights, right) for right in REQUIRED_BOT_PRIVILEGES]
        ):
            logger.exception(
                f"Bot user has no rights to invite users: {chat_identifier!r}"
            )
            raise TelegramChatNotSufficientPrivileges(
                f"Bot user has no rights to change chat info: {chat_identifier!r}"
            )

        return chat

    async def _load_participants(self, chat_identifier: int) -> None:
        """
        Loads participants of a specified chat and processes their data.

        This asynchronous method retrieves participants of the given chat using the
        Telethon service, processes each participant's information, and stores it in
        the database. Bot users are excluded from processing. Additionally, it
        determines participant admin status and stores the associated chat-user
        relationship.

        :param chat_identifier: The unique identifier of the chat whose participants
            are to be loaded
        :return: This method does not return a value
        """
        user_service = UserService(self.db_session)
        logger.info(f"Loading chat participants for chat {chat_identifier!r}...")

        await self.telethon_service.start()

        async for participant_user in self.telethon_service.get_participants(
            chat_identifier
        ):
            if participant_user.bot:
                # Don't index bot users
                continue

            user = user_service.create_or_update(
                TelegramUserDTO(
                    id=participant_user.id,
                    first_name=participant_user.first_name or "",
                    last_name=participant_user.last_name,
                    username=participant_user.username,
                    is_premium=participant_user.premium or False,
                    language_code=participant_user.lang_code
                    or core_settings.default_language,
                )
            )
            self.telegram_chat_user_service.create_or_update(
                chat_id=chat_identifier,
                user_id=user.id,
                is_admin=hasattr(participant_user.participant, "admin_rights"),
                is_managed=False,
            )
        logger.info(f"Chat participants loaded for chat {chat_identifier!r}")

    async def index(self, chat: ChatPeerType) -> None:
        """
        Handles the process of creating and refreshing a Telegram chat invite link,
        and loading the participants for the given chat. If the chat already has an
        invite link, it skips the creation process.

        :param chat: An instance of the ChatPeerType representing the Telegram chat.
        :return: None
        """
        chat_id = get_peer_id(chat, add_mark=True)
        telegram_chat = self.telegram_chat_service.get(chat_id=chat_id)

        if not telegram_chat.invite_link:
            logger.info(f"Creating a new chat invite link for the chat {chat_id!r}...")
            invite_link = await self.telethon_service.get_invite_link(chat)
            self.telegram_chat_service.refresh_invite_link(chat_id, invite_link.link)
        logger.info(f"Chat {chat_id!r} created successfully")
        await self._load_participants(telegram_chat.id)

    async def fetch_and_push_profile_photo(self, chat: ChatPeerType) -> Path | None:
        """
        Fetches the profile photo of a chat and uploads it for hosting. This function
        handles the download of the profile photo from the given chat and then pushes
        it to a CDN service for further access. If the profile photo exists, it will
        be returned as a Path object; otherwise, None is returned.

        :param chat: The chat from which the profile photo is to be fetched.
        :return: The local path of the fetched profile photo or None
        """
        logo_path = await self.telethon_service.download_profile_photo(chat)
        if logo_path:
            await self.cdn_service.upload_file(
                file_path=logo_path,
                object_name=logo_path.name,
            )
            logger.info(f"Profile photo for chat {chat.id!r} uploaded")
        return logo_path

    async def _create(
        self, chat: ChatPeerType, sufficient_bot_privileges: bool = False
    ) -> BaseTelegramChatDTO:
        """
        Creates a new BaseTelegramChatDTO instance by fetching and storing the profile photo of the chat,
        generating the appropriate chat identifier, and persisting the chat information.

        If the chat already exists in the database, the function raises the TelegramChatAlreadyExists
        exception and logs the occurrence. The method supports handling cases where the bot does not have
        sufficient privileges and reflects this in the resultant DTO.

        :param chat: The chat entity for which the BaseTelegramChatDTO is created.
        :param sufficient_bot_privileges: Indicates whether the bot has sufficient privileges within the chat. Defaults to False.
        :return: A DTO containing the details of the created Telegram chat.
        :raises TelegramChatAlreadyExists: If the chat already exists in the database.
        """
        logo_path = await self.fetch_and_push_profile_photo(chat)
        try:
            chat_id = get_peer_id(chat, add_mark=True)
            telegram_chat = self.telegram_chat_service.create(
                chat_id=chat_id,
                entity=chat,
                logo_path=logo_path.name if logo_path else None,
            )
            return BaseTelegramChatDTO(
                id=telegram_chat.id,
                username=telegram_chat.username,
                title=telegram_chat.title,
                description=telegram_chat.description,
                slug=telegram_chat.slug,
                is_forum=telegram_chat.is_forum,
                logo_path=telegram_chat.logo_path,
                insufficient_privileges=not sufficient_bot_privileges,
            )
        except sqlalchemy.exc.IntegrityError:
            logger.exception(f"Chat {chat.stringify()!r} already exists")
            raise TelegramChatAlreadyExists(f"Chat {chat.stringify()!r} already exists")

    async def create(
        self, chat_identifier: int, sufficient_bot_privileges: bool = False
    ) -> BaseTelegramChatDTO:
        """
        Creates a new Telegram chat entry based on the provided chat identifier and bot privileges.

        This function retrieves data for a chat using the given identifier, processes it to
        create a Telegram chat entry, and optionally indexes the chat for further use. The
        process involves handling Telegram-specific logic and ensuring sufficient privileges
        are taken into account when creating the chat.

        :param chat_identifier: An integer identifier for the Telegram chat whose data
            is to be retrieved and processed.
        :param sufficient_bot_privileges: A boolean indicating whether the bot has sufficient
            privileges to perform the requested operation. Defaults to False.
        :return: A BaseTelegramChatDTO object representing the created Telegram chat data.
        """
        chat = await self._get_chat_data(chat_identifier)
        telegram_chat_dto = await self._create(
            chat, sufficient_bot_privileges=sufficient_bot_privileges
        )
        logger.info(f"Chat {chat.id!r} created successfully")
        await self.index(chat)
        logger.info(f"Chat {chat.id!r} indexed successfully")
        return telegram_chat_dto

    async def refresh_all(self) -> None:
        """
        Refreshes all Telegram chats available through the `telegram_chat_service`.
        This method iterates through all chats, attempting to refresh them
        by calling a private method. If a chat does not exist or the bot does not have
        the necessary privileges, those specific exceptions are caught and ignored,
        and the iteration continues with other chats.

        :raises TelegramChatNotExists:
            Raised if a chat does not exist because it was deleted or the bot was
            removed from the chat.
        :raises TelegramChatNotSufficientPrivileges:
            Raised if the bot lacks sufficient privileges to function in the chat.

        :return: This function does not return a value as its primary purpose is to
            refresh all accessible chats.
        """
        for chat in self.telegram_chat_service.get_all():
            try:
                await self._refresh(chat)
            except (
                TelegramChatNotExists,  # happens when chat is deleted or bot is removed from the chat
                TelegramChatNotSufficientPrivileges,  # happens when bot has no rights to function in the chat
            ):
                continue

    async def _refresh(self, chat: TelegramChat) -> TelegramChat:
        """
        Refresh and update the details of a specified Telegram chat.

        This method retrieves and updates the latest details of the provided Telegram
        chat. In the case where the chat has been deleted or the bot does not have
        sufficient privileges, warnings are logged, and the chat is marked with
        insufficient permissions instead of being refreshed.

        :param chat: Telegram chat instance that needs to be refreshed
        :return: The updated Telegram chat instance
        :raises TelegramChatNotExists: If the chat no longer exists or the bot was removed from the chat
        :raises TelegramChatNotSufficientPrivileges: If the bot lacks functionality privileges within the chat
        """
        try:
            chat_entity, logo_path = await self._get_chat_data(chat.id)

        except (
            TelegramChatNotSufficientPrivileges,  # happens when bot has no rights to function in the chat
        ):
            logger.warning(
                f"Chat {chat.id!r} has insufficient permissions set. Disabling it..."
            )
            self.telegram_chat_service.set_insufficient_privileges(chat_id=chat.id)
            raise

        except (
            TelegramChatNotExists,  # happens when chat is deleted or bot is removed from the chat
        ):
            logger.warning(f"Chat {chat.id!r} not found. Removing it...")
            self.telegram_chat_service.delete(chat_id=chat.id)
            raise

        chat = self.telegram_chat_service.update(
            chat=chat,
            entity=chat_entity,
            logo_path=logo_path.name,
        )
        await self.index(chat_entity)
        logger.info(f"Chat {chat.id!r} refreshed successfully")
        return chat

    async def get_with_eligibility_summary(
        self, slug: str, user: User
    ) -> TelegramChatWithEligibilitySummaryDTO:
        """
        This is non-administrative method to get chat with rules
        :param slug:
        :param user:
        :return:
        :raises TelegramChatNotExists: if chat with slug not found
        """
        try:
            chat = self.telegram_chat_service.get_by_slug(slug)
        except NoResultFound:
            logger.warning(f"Chat with slug {slug!r} not found")
            raise TelegramChatNotExists(f"Chat with slug {slug!r} not found")
        eligibility_summary = self.authorization_action.is_user_eligible_chat_member(
            chat_id=chat.id,
            user_id=user.id,
        )
        is_chat_member = self.telegram_chat_user_service.is_chat_member(
            chat_id=chat.id,
            user_id=user.id,
        )
        is_eligible = bool(eligibility_summary)

        mapping = {
            EligibilityCheckType.NFT_COLLECTION: NftRuleEligibilitySummaryDTO,
        }

        return TelegramChatWithEligibilitySummaryDTO(
            chat=TelegramChatDTO.from_object(
                chat,
                join_url=chat.invite_link if is_eligible else None,
                is_member=is_chat_member,
                is_eligible=is_eligible,
            ),
            rules=[
                mapping.get(rule.type, RuleEligibilitySummaryDTO).from_internal_dto(
                    rule
                )
                for rule in eligibility_summary.items
            ],
            wallet=eligibility_summary.wallet,
        )


class TelegramChatManageAction(ManagedChatBaseAction, TelegramChatAction):
    def __init__(
        self,
        db_session: Session,
        requestor: User,
        chat_slug: str,
    ) -> None:
        super().__init__(db_session, requestor, chat_slug)

    async def refresh(self) -> BaseTelegramChatDTO:
        """
        Refreshes a Telegram chat by its slug, and updates the related information.

        This method retrieves a Telegram chat using the provided slug, updates its
        details by performing a refresh operation, and constructs a new data transfer
        object (DTO) with the updated chat properties. If the chat is not found, an
        exception is raised to indicate that the specified Telegram chat does not
        exist.
        :return: A data transfer object containing the updated chat properties.
        :raises TelegramChatNotExists: If no chat is found for the given slug.
        """
        chat = await self._refresh(self.chat)
        return BaseTelegramChatDTO(
            id=chat.id,
            username=chat.username,
            title=chat.title,
            description=chat.description,
            slug=chat.slug,
            is_forum=chat.is_forum,
            logo_path=chat.logo_path,
        )

    async def update(self, description: str | None) -> BaseTelegramChatDTO:
        """
        Updates the description of a Telegram chat with the specified slug.

        This method retrieves a Telegram chat by its slug, updates its description
        if the chat exists, and returns a DTO containing the updated chat information.
        If the chat does not exist, an exception is raised.

        :param description: The new description for the Telegram chat. If None, the
            description will be cleared.
        :return: A Data Transfer Object (DTO) representing the updated Telegram chat,
            containing its unique id, username, title, description, slug, forum flag,
            and logo path.
        :raises TelegramChatNotExists: If no chat is found with the given slug.
        """
        chat = self.telegram_chat_service.update_description(
            chat=self.chat,
            description=description,
        )

        return BaseTelegramChatDTO(
            id=chat.id,
            username=chat.username,
            title=chat.title,
            description=chat.description,
            slug=chat.slug,
            is_forum=chat.is_forum,
            logo_path=chat.logo_path,
        )

    async def get_with_eligibility_rules(self) -> TelegramChatWithRulesDTO:
        """
        This is administrative method to get chat with rules that includes disabled rules
        :return: DTO with chat and rules
        """
        eligibility_rules = self.authorization_action.get_eligibility_rules(
            chat_id=self.chat.id,
            enabled_only=False,
        )

        return TelegramChatWithRulesDTO(
            chat=TelegramChatDTO.from_object(
                obj=self.chat,
                join_url=self.chat.invite_link,
                is_member=False,
                is_eligible=False,
            ),
            rules=sorted(
                [
                    *(
                        RuleEligibilitySummaryDTO.from_toncoin_rule(rule)
                        for rule in eligibility_rules.toncoin
                    ),
                    *(
                        RuleEligibilitySummaryDTO.from_jetton_rule(rule)
                        for rule in eligibility_rules.jettons
                    ),
                    *(
                        NftEligibilityRuleDTO.from_nft_collection_rule(rule)
                        for rule in eligibility_rules.nft_collections
                    ),
                    *(
                        RuleEligibilitySummaryDTO.from_whitelist_rule(rule)
                        for rule in eligibility_rules.whitelist_sources
                    ),
                    *(
                        RuleEligibilitySummaryDTO.from_whitelist_external_rule(rule)
                        for rule in eligibility_rules.whitelist_external_sources
                    ),
                    *(
                        RuleEligibilitySummaryDTO.from_premium_rule(rule)
                        for rule in eligibility_rules.premium
                    ),
                ],
                key=lambda rule: (not rule.is_enabled, rule.type.value, rule.title),
            ),
        )

    async def delete(self) -> None:
        self.telegram_chat_service.delete(self.chat.id)
