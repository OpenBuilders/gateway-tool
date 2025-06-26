import logging
from tempfile import NamedTemporaryFile

from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session
from telethon import types, TelegramClient, Button
from telethon.errors import (
    BadRequestError,
    PeerIdInvalidError,
    HideRequesterMissingError,
    RPCError,
)
from telethon.utils import get_peer_id

from community_manager.dtos.chat import TargetChatMembersDTO
from community_manager.events import ChatAdminChangeEventBuilder
from community_manager.settings import community_manager_settings
from core.actions.authorization import AuthorizationAction
from core.actions.base import BaseAction
from core.actions.user import UserAction
from core.constants import (
    UPDATED_WALLETS_SET_NAME,
    UPDATED_STICKERS_USER_IDS,
    UPDATED_GIFT_USER_IDS,
    REQUIRED_BOT_PRIVILEGES,
)
from core.dtos.chat import TelegramChatDTO
from core.dtos.user import TelegramUserDTO
from core.exceptions.chat import (
    TelegramChatNotExists,
    TelegramChatNotSufficientPrivileges,
    TelegramChatPublicError,
    TelegramChatAlreadyExists,
)
from core.models.chat import TelegramChat
from core.services.cdn import CDNService
from core.services.chat import TelegramChatService
from core.services.chat.rule.gift import TelegramChatGiftCollectionService
from core.services.chat.rule.sticker import TelegramChatStickerCollectionService
from core.services.chat.user import TelegramChatUserService
from core.services.superredis import RedisService
from core.services.supertelethon import ChatPeerType, TelethonService
from core.services.user import UserService

logger = logging.getLogger(__name__)


class CommunityManagerChatAction(BaseAction):
    def __init__(
        self, db_session: Session, telethon_client: TelegramClient | None = None
    ) -> None:
        super().__init__(db_session)
        self.telegram_chat_service = TelegramChatService(db_session)
        self.telegram_chat_user_service = TelegramChatUserService(db_session)
        self.redis_service = RedisService()
        self.cdn_service = CDNService()
        self.authorization_action = AuthorizationAction(
            db_session, telethon_client=telethon_client
        )
        self.telethon_service = TelethonService(
            client=telethon_client,
            bot_token=community_manager_settings.telegram_bot_token,
        )

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

        # breakpoint()

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
        the database.
        Bot users are excluded from processing.
        Additionally, it determines participant admin status and stores the associated chat-user
        relationship.

        :param chat_identifier: The unique identifier of the chat whose participants
            are to be loaded
        :return: This method does not return a value
        """
        user_action = UserAction(self.db_session)
        logger.info(f"Loading chat participants for chat {chat_identifier!r}...")

        await self.telethon_service.start()

        async for participant_user in self.telethon_service.get_participants(
            chat_identifier
        ):
            if participant_user.bot:
                # Don't index bot users
                continue

            user = user_action.create_or_update(
                TelegramUserDTO.from_telethon_user(participant_user)
            )
            self.telegram_chat_user_service.create_or_update(
                chat_id=chat_identifier,
                user_id=user.id,
                is_admin=hasattr(participant_user.participant, "admin_rights"),
                is_managed=False,
            )
        logger.info(f"Chat participants loaded for chat {chat_identifier!r}")

    async def _index(self, chat: ChatPeerType) -> None:
        """
        Handles the process of creating and refreshing a Telegram chat invite link
        and loading the participants for the given chat.
        If the chat already has an invitation link, it skips the creation process.

        :param chat: An instance of the ChatPeerType representing the Telegram chat.
        :return: None
        """
        chat_id = get_peer_id(chat, add_mark=True)
        telegram_chat = self.telegram_chat_service.get(chat_id=chat_id)

        if not telegram_chat.invite_link:
            logger.info(f"Creating a new chat invite link for the chat {chat_id!r}...")
            invite_link = await self.telethon_service.get_invite_link(chat)
            self.telegram_chat_service.refresh_invite_link(chat_id, invite_link.link)
        await self._load_participants(telegram_chat.id)

    async def _create(
        self, chat: ChatPeerType, sufficient_bot_privileges: bool = False
    ) -> TelegramChatDTO:
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
        logo_path = await self.fetch_and_push_profile_photo(
            chat, current_logo_path=None
        )
        try:
            chat_id = get_peer_id(chat, add_mark=True)
            telegram_chat = self.telegram_chat_service.create(
                chat_id=chat_id,
                entity=chat,
                logo_path=logo_path,
            )
            return TelegramChatDTO.from_object(
                obj=telegram_chat, insufficient_privileges=not sufficient_bot_privileges
            )
        except IntegrityError:
            logger.exception(f"Chat {chat.stringify()!r} already exists")
            raise TelegramChatAlreadyExists(f"Chat {chat.stringify()!r} already exists")

    async def create(
        self, chat_id: int, event: ChatAdminChangeEventBuilder.Event
    ) -> TelegramChatDTO:
        """
        Asynchronously creates a Telegram chat in the system by handling events related to
        chat administrator changes, maintaining synchronization with incoming data.

        The function performs several operations, including fetching chat information,
        validating chat state (e.g., admin rights and visibility), creating the chat entity,
        and indexing it for further operations. Additionally, it calculates the members count
        to provide an updated representation of the chat entity.

        :param chat_id: Unique identifier of the Telegram chat.
        :param event: Event data containing information about changes in chat administrator rights.
        :return: A data transfer object representing the newly created and processed Telegram chat.
        """
        if not event.is_self or not event.sufficient_bot_privileges:
            logger.debug(
                f"Chat {chat_id!r} doesn't exist, but bot was added without admin rights. Skipping."
            )

        chat = await self._get_chat_data(chat_id)
        if chat.username:
            logger.warning(
                f"Bot added to the public chat/channel {chat.username!r}. Skipping..."
            )
            raise TelegramChatPublicError(f"Chat {chat.username!r} is public.")
        telegram_chat_dto = await self._create(
            chat, sufficient_bot_privileges=event.sufficient_bot_privileges
        )
        logger.info(f"Chat {chat.id!r} created successfully")
        await self._index(chat)
        logger.info(f"Chat {chat.id!r} indexed successfully")
        members_count = self.telegram_chat_user_service.get_members_count(
            telegram_chat_dto.id
        )
        return TelegramChatDTO.model_validate(
            {**telegram_chat_dto.model_dump(), "members_count": members_count}
        )

    async def refresh_all(self) -> None:
        """
        Refreshes all Telegram chats available through the `telegram_chat_service`.
        This method iterates through all chats, attempting to refresh them
        by calling a private method.
        If a chat does not exist or the bot does not have the necessary privileges,
        those specific exceptions are caught and ignored, and the iteration continues with other chats.

        :raises TelegramChatNotExists:
            Raised if a chat does not exist because it was deleted or the bot was
            removed from the chat.
        :raises TelegramChatNotSufficientPrivileges:
            Raised if the bot lacks enough privileges to function in the chat.

        :return: This function does not return a value as its primary purpose is to
            refresh all accessible chats.
        """
        for chat in self.telegram_chat_service.get_all(
            enabled_only=True,
            sufficient_privileges_only=True,
        ):
            try:
                await self._refresh(chat)
            except Exception as e:
                logger.exception(
                    f"Unexpected error occurred while refreshing chat {chat.id!r}",
                    exc_info=e,
                )

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
            chat_entity = await self._get_chat_data(chat.id)

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

        logo_path = await self.fetch_and_push_profile_photo(
            chat_entity, current_logo_path=chat.logo_path
        )

        chat = self.telegram_chat_service.update(
            chat=chat,
            entity=chat_entity,
            # If a new logo was downloaded - use it,
            #  otherwise fallback to the current one
            logo_path=logo_path or chat.logo_path,
        )
        await self._index(chat_entity)
        logger.info(f"Chat {chat.id!r} refreshed successfully")
        return chat

    async def fetch_and_push_profile_photo(
        self,
        chat: ChatPeerType,
        current_logo_path: str | None,
    ) -> str | None:
        """
        Fetches the profile photo of a chat and uploads it for hosting. This function
        handles the download of the profile photo from the given chat and then pushes
        it to a CDN service for further access. If the profile photo exists, it will
        be returned as a Path object; otherwise, None is returned.

        :param chat: The chat from which the profile photo is to be fetched.
        :param current_logo_path: The current logo path in the database.
        :return: The local path of the fetched profile photo or None
        """
        with NamedTemporaryFile(suffix=".png", mode="w+b", delete=True) as f:
            logo_path = await self.telethon_service.download_profile_photo(
                entity=chat,
                target_location=f,
                current_logo_path=current_logo_path,
            )
            if logo_path:
                await self.cdn_service.upload_file(
                    file_path=f.name,
                    object_name=logo_path,
                )
                logger.info(f"New profile photo for chat {chat.id!r} uploaded")
                return logo_path

        return None

    async def on_logo_update(
        self, chat: ChatPeerType, photo: types.Photo | None
    ) -> None:
        """
        Handles the event when a chat logo is updated, either by setting a new logo or removing an existing one.

        This method is triggered automatically when a logo update event occurs.
        If the logo is removed (`photo` is `None`),
        it logs the deletion event and clears the stored logo information for the specific chat.
        If a new logo is set, it invokes further processing to handle the update.

        :param chat: The chat peer object that represents the source of the logo update event.
        :param photo: An object representing the new photo/logo set for the chat, or `None`
            if the photo was removed.
        """
        chat_id = get_peer_id(chat, add_mark=True)
        if not photo:
            logger.info(f"Logo for the chat {chat_id!r} was deleted")
            self.telegram_chat_service.clear_logo(chat_id=chat_id)
        else:
            await self.on_new_logo_set(chat)

    async def on_new_logo_set(self, chat: ChatPeerType) -> None:
        """
        Handles the event of a new logo being set for the chat, updates the
        chat logo by fetching and storing the new logo image, and integrates it
        with the relevant chat settings.

        :param chat: Represents the chat for which the new logo was set.
        """
        chat_id = get_peer_id(chat, add_mark=True)

        logo_path = await self.fetch_and_push_profile_photo(
            chat,
            # We definitely know here that the new photo was set - no need to fetch the current value
            current_logo_path=None,
        )

        if logo_path:
            logger.info(
                f"Updating logo for chat {chat_id!r} with path {logo_path!r}..."
            )
            self.telegram_chat_service.set_logo(chat_id=chat_id, logo_path=logo_path)
            logger.info(f"Updated logo for chat {chat_id!r} with path {logo_path!r}..")
        else:
            logger.warning(
                f"Ignoring update for chat {chat_id!r} as logo was not downloaded.."
            )

    async def on_title_update(self, chat_id: int, new_title: str) -> None:
        logger.info(f"Updating title for chat {chat_id!r} with title {new_title!r}...")
        self.telegram_chat_service.set_title(
            chat_id=chat_id,
            title=new_title,
        )
        logger.info(f"Updated title for chat {chat_id!r} with title {new_title!r}..")

    async def on_chat_member_in(
        self,
        user: TelegramUserDTO,
        chat_id: int,
    ) -> None:
        """
        Handle the event when users join the chat without being approved by bot
        :param user: Users that joined the chat
        :param chat_id: Chat ID
        :return:
        """
        await self.telethon_service.start()
        chat = self.telegram_chat_service.get(chat_id)
        user_action = UserAction(self.db_session)
        local_user = user_action.get_or_create(user)

        # If chat is not fully controlled and user was added -
        #  just ignore it and create entity in the database
        if not chat.is_full_control or not chat.is_enabled:
            self.telegram_chat_user_service.create_or_update(
                chat_id=chat_id,
                user_id=local_user.id,
                is_admin=False,
                is_managed=False,
            )
            return
        # If the bot fully controls chat - check the user eligibility
        #  and only then create a new chat member record
        elif (
            eligibility_summary
            := self.authorization_action.is_user_eligible_chat_member(
                user_id=local_user.id, chat_id=chat_id
            )
        ):
            self.telegram_chat_user_service.create_or_update(
                chat_id=chat_id, user_id=local_user.id, is_admin=False, is_managed=True
            )
            logger.debug(
                f"User {local_user.telegram_id!r} was added to chat {chat_id!r}"
            )
        # If user is not eligible - kick it from the chat
        else:
            await self.telethon_service.kick_chat_member(
                chat_id=chat_id, telegram_user_id=local_user.telegram_id
            )
            logger.warning(
                f"User {local_user.telegram_id!r} is not eligible to join chat {chat_id!r} even though was added. Kicking the user",
                extra={
                    "eligibility_summary": eligibility_summary,
                },
            )

    async def on_bot_kicked(self, chat_id: int) -> None:
        """
        Handle the event when the bot is kicked from the chat
        :param chat_id: Chat ID
        """
        telegram_chat_service = TelegramChatService(self.db_session)
        telegram_chat_service.delete(chat_id=chat_id)
        logger.info(f"Chat {chat_id!r} was removed as bot was kicked from it.")

    async def on_chat_member_out(
        self,
        user: TelegramUserDTO,
        chat_id: int,
    ) -> None:
        """
        Handle the event when users leave the chat
        :param chat_id: Chat ID
        :param user: User that left the chat
        """
        try:
            local_user = self.user_service.get_by_telegram_id(telegram_id=user.id)
            self.telegram_chat_user_service.delete(
                chat_id=chat_id, user_id=local_user.id
            )
        except NoResultFound:
            logger.debug(f"No user {user.id!r} found in the database. Skipping.")

    async def on_chat_member_update(
        self,
        event: ChatAdminChangeEventBuilder.Event,
        chat: TelegramChatDTO,
    ) -> None:
        user_action = UserAction(self.db_session)
        target_user = user_action.get_or_create(
            telegram_user=TelegramUserDTO.from_telethon_user(event.user)
        )

        try:
            target_chat_user = self.telegram_chat_user_service.get(
                chat_id=chat.id, user_id=target_user.id
            )
        except NoResultFound:
            logger.info(
                f"No chat user found in chat {chat.id!r} for user {target_user.id!r}. Creating..."
            )
            self.telegram_chat_user_service.create(
                chat_id=chat.id,
                user_id=target_user.id,
                is_admin=event.has_enough_rights,
                # Because it was not added by the bot user
                is_managed=False,
            )
            return

        # Handle admin privileges update on the normal user
        if event.is_demoted or not event.has_enough_rights:
            if target_chat_user.is_admin:
                logger.info("Admin %d demoted in chat %d", target_user.id, chat.id)
                self.telegram_chat_user_service.demote_admin(
                    chat_id=chat.id, user_id=target_chat_user.user_id
                )

        elif event.has_enough_rights:
            if not target_chat_user.is_admin:
                logger.info("Admin %d promoted in chat %d", target_user.id, chat.id)
                self.telegram_chat_user_service.promote_admin(
                    chat_id=chat.id,
                    user_id=target_user.id,
                )

    async def on_bot_chat_member_update(
        self, event: ChatAdminChangeEventBuilder.Event, chat: TelegramChatDTO
    ) -> None:
        """
        Handles updates related to the current bot user's permissions and privileges
        in a Telegram chat. This includes actions such as logging permission changes,
        and updating internal state if the bot's privileges in the chat become
        sufficient or insufficient.

        :param event: Event representing admin change updates in the chat.
        :param chat: Data Transfer Object (DTO) for the Telegram chat.
        """
        # Handling updates for the current bot user
        logger.info(
            "The Bot user privileges are managed in the chat %d: %s",
            chat.id,
            event.new_participant,
        )
        if not event.sufficient_bot_privileges:
            if not chat.insufficient_privileges:
                logger.warning(
                    "Insufficient permissions for the bot in chat %d", chat.id
                )
                self.telegram_chat_service.set_insufficient_privileges(
                    chat_id=chat.id, value=True
                )
        elif chat.insufficient_privileges:
            logger.info("Sufficient permissions for the bot in chat %d", chat.id)
            self.telegram_chat_service.set_insufficient_privileges(
                chat_id=chat.id, value=False
            )

    async def on_join_request(
        self,
        telegram_user_id: int,
        chat_id: int,
        invited_by_bot: bool = False,
        invite_link: str | None = None,
    ) -> None:
        """
        Handles join requests for a chat and take appropriate action based on the bot’s
        permissions, the chat's status, and the user's eligibility.

        This method is intended to process join requests for Telegram chats where the
        bot is present. Depending on the chat's configuration and the user's eligibility,
        it will either approve or decline the join request. It also handles other related
        tasks such as revoking invite links if a chat is disabled or updating user-chat
        relations in the database.

        :param telegram_user_id: The unique identifier of the Telegram user making the
            join request.
        :param chat_id: The unique identifier of the Telegram chat where the join
            request was made.
        :param invited_by_bot: Indicates whether the user was invited by the bot.
        :param invite_link: The invite link used by the user, if available.
        """
        try:
            chat = self.telegram_chat_service.get(chat_id)
        except NoResultFound:
            # If bot sees the join request - it should be an admin, means chat should exist. Raise a flag
            logger.warning(f"Chat {chat_id!r} does not exist in the database.")
            return

        if chat.insufficient_privileges:
            logger.warning(
                f"User join request {telegram_user_id=} and {chat_id=} "
                f"can't be approved or rejected as bot lacks privileges to manage the chat. Skipping."
            )
            return

        if not chat.is_enabled and invited_by_bot and invite_link is not None:
            await self.telethon_service.start()
            try:
                logger.warning(
                    f"Declining join request from user {telegram_user_id!r} for chat {chat_id!r} as it is disabled. "
                )
                await self.telethon_service.decline_chat_join_request(
                    chat_id=chat_id, telegram_user_id=telegram_user_id
                )
                logger.warning(
                    f"Chat {chat_id!r} is disabled. Revoking the invite link."
                )
                await self.telethon_service.revoke_chat_invite(
                    chat_id=chat_id, link=invite_link
                )
            except HideRequesterMissingError as e:
                logger.warning(f"Join request is already handled. Skipping. {e!r}")
            except RPCError:
                logger.exception("Error while removing invite link.")

            return

        logger.info(f"New join request: {telegram_user_id=!r} to join {chat_id=!r}")

        if not chat.is_full_control and not invited_by_bot:
            logger.warning(
                f"The user {telegram_user_id!r} was not invited by the bot"
                f" and the chat {chat_id!r} is not fully managed. Should be handled manually.",
            )
            return

        await self.telethon_service.start()
        telegram_user = await self.telethon_service.get_user(telegram_user_id)
        user_action = UserAction(self.db_session)
        local_user = user_action.get_or_create(
            TelegramUserDTO.from_telethon_user(telegram_user)
        )
        if (
            eligibility_summary
            := self.authorization_action.is_user_eligible_chat_member(
                user_id=local_user.id, chat_id=chat_id
            )
        ):
            await self.telethon_service.approve_chat_join_request(
                chat_id=chat_id, telegram_user_id=local_user.telegram_id
            )
            if local_user.allows_write_to_pm:
                try:
                    await self.telethon_service.send_message(
                        chat_id=telegram_user_id,
                        message=f"You join request for **{chat.title}** was successfully approved! 🎉\n\nWelcome aboard! 🚀",
                        buttons=[[Button.url("Open Chat", chat.invite_link)]],
                    )
                except PeerIdInvalidError as e:
                    logger.warning(
                        f"Can't send confirmation message to user {telegram_user_id=!r}: {e.message}"
                    )
            self.telegram_chat_user_service.create_or_update(
                chat_id=chat_id,
                user_id=local_user.id,
                is_admin=False,
                is_managed=True,
            )
            logger.info(
                f"User {local_user.telegram_id!r} was approved to join chat {chat_id!r}",
                extra={
                    "eligibility_summary": eligibility_summary,
                },
            )
        else:
            await self.telethon_service.decline_chat_join_request(
                chat_id=chat_id, telegram_user_id=local_user.telegram_id
            )
            logger.info(
                f"User {local_user.telegram_id!r} is not eligible to join chat {chat_id!r}. Declining the request.",
                extra={
                    "eligibility_summary": eligibility_summary,
                },
            )


class CommunityManagerTaskChatAction:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.user_service = UserService(db_session)
        self.telegram_chat_user_service = TelegramChatUserService(db_session)
        self.telegram_chat_sticker_collection_service = (
            TelegramChatStickerCollectionService(db_session)
        )
        self.telegram_chat_gift_collection_service = TelegramChatGiftCollectionService(
            db_session
        )
        self.redis_service = RedisService()

    def get_updated_chat_members(self) -> TargetChatMembersDTO:
        """
        Fetches and updates the target chat members based on specific criteria, including
        linked wallets and sticker owners. The method retrieves updated wallet addresses
        and sticker owner IDs from the Redis service, identifies relevant chat members
        from the Telegram chat services, and compiles the processed data into a
        `TargetChatMembersDTO` object.

        :raises ValueError: If unexpected data types are retrieved or processed in the logic.

        :return: A `TargetChatMembersDTO` object containing the updated wallet addresses,
            sticker owner IDs, and the compiled target chat members.
        """
        wallets = self.redis_service.pop_from_set(
            name=UPDATED_WALLETS_SET_NAME,
            count=community_manager_settings.items_per_task,
        )
        if isinstance(wallets, str):
            wallets = [wallets]

        sticker_owners_telegram_ids = (
            self.redis_service.pop_from_set(
                name=UPDATED_STICKERS_USER_IDS,
                count=community_manager_settings.items_per_task,
            )
            or []
        )
        if isinstance(sticker_owners_telegram_ids, str):
            sticker_owners_telegram_ids = [sticker_owners_telegram_ids]
        sticker_owners_telegram_ids = set(map(int, sticker_owners_telegram_ids))

        gift_owners_telegram_ids = (
            self.redis_service.pop_from_set(
                name=UPDATED_GIFT_USER_IDS,
                count=community_manager_settings.items_per_task,
            )
            or []
        )

        if isinstance(gift_owners_telegram_ids, str):
            gift_owners_telegram_ids = [gift_owners_telegram_ids]
        gift_owners_telegram_ids = set(map(int, gift_owners_telegram_ids))

        target_chat_members: set[tuple[int, int]] = set()

        if wallets:
            chat_members = self.telegram_chat_user_service.get_all_by_linked_wallet(
                addresses=wallets
            )
            target_chat_members.update(
                {(cm.chat_id, cm.user_id) for cm in chat_members}
            )

        sticker_rules_chat_ids = {}
        gift_rules_chat_ids = {}

        if sticker_owners_telegram_ids:
            rules = self.telegram_chat_sticker_collection_service.get_all(
                enabled_only=True
            )
            sticker_rules_chat_ids = {r.chat_id for r in rules}

        if gift_owners_telegram_ids:
            rules = self.telegram_chat_gift_collection_service.get_all(
                enabled_only=True,
            )
            gift_rules_chat_ids = {r.chat_id for r in rules}

        for chat_ids, user_ids in zip(
            (sticker_rules_chat_ids, gift_rules_chat_ids),
            (sticker_owners_telegram_ids, gift_owners_telegram_ids),
        ):
            users = self.user_service.get_all(telegram_ids=user_ids)
            chat_members = self.telegram_chat_user_service.get_all(
                user_ids=[user.id for user in users],
                chat_ids=list(chat_ids),
                with_wallet_details=False,
            )
            target_chat_members.update(
                {
                    (chat_member.chat_id, chat_member.user_id)
                    for chat_member in chat_members
                }
            )

        return TargetChatMembersDTO(
            wallets=wallets,
            sticker_owners_ids=list(sticker_owners_telegram_ids),
            target_chat_members=target_chat_members,
        )

    async def sanity_chat_checks(self, telethon_client: TelegramClient) -> None:
        """
        Performs sanity checks on chat members and validates their eligibility. If there are
        any chat members to validate, it initiates the validation process with the help of
        a Telegram service client. Ineligible members are removed based on the validation
        logic. If an error occurs during validation, a fallback mechanism is triggered
        to add wallets and users back to the redis database to try again later.

        The method logs the progress at various stages and handles exceptions to ensure
        fallback processes are executed if needed.

        :raises Exception: If validation of chat members fails during execution.
        """
        dto = self.get_updated_chat_members()
        if target_chat_members := dto.target_chat_members:
            try:
                logger.info(f"Validating chat members for {target_chat_members}")
                chat_members = self.telegram_chat_user_service.get_all_pairs(
                    chat_member_pairs=target_chat_members
                )

                if not chat_members:
                    logger.info("No chats to validate. Skipping")
                    return
                else:
                    logger.info(f"Found {len(chat_members)} chat members to validate")

                authorization_action = AuthorizationAction(
                    self.db_session, telethon_client=telethon_client
                )
                await authorization_action.kick_ineligible_chat_members(
                    chat_members=chat_members
                )
                logger.info(
                    f"Successfully validated {len(chat_members)} chat members. "
                )
            except Exception as exc:
                logger.error(f"Failed to validate chat members: {exc}", exc_info=True)
                self.fallback_update_chat_members(dto=dto)
                raise exc
        else:
            logger.info("No users to validate. Skipping")

    def fallback_update_chat_members(self, dto: TargetChatMembersDTO) -> None:
        """
        Activates a fallback mechanism to update chat members by storing provided wallets
        and sticker owner IDs in Redis sets. This ensures that the required updates are
        persisted and managed separately if the primary update mechanism fails.

        :param dto: A data transfer object containing the wallets and sticker owner IDs
            to be updated in Redis sets.
        """
        logger.warning("Activating fallback method for chat members.")
        if dto.wallets:
            self.redis_service.add_to_set(UPDATED_WALLETS_SET_NAME, *dto.wallets)
        if dto.sticker_owners_ids:
            self.redis_service.add_to_set(
                UPDATED_STICKERS_USER_IDS, *map(str, dto.sticker_owners_ids)
            )
