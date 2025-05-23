import logging
from typing import AsyncGenerator, IO, BinaryIO

from telethon import TelegramClient, Button
from telethon.sessions import MemorySession
from telethon.tl.functions.messages import (
    ExportChatInviteRequest,
    HideChatJoinRequestRequest,
    EditExportedChatInviteRequest,
)
from telethon.tl.types import (
    User as TelethonUser,
    Channel,
    ChatInviteExported,
    InputPeerChat,
    InputPeerChannel,
    InputPeerUser,
    InputUser,
    ChatPhotoEmpty,
)

from core.settings import core_settings

logger = logging.getLogger(__name__)


ChatPeerType = Channel | InputPeerChat | InputPeerChannel
UserPeerType = TelethonUser | InputPeerUser | InputUser


class TelethonService:
    def __init__(self, client: TelegramClient | None = None) -> None:
        """
        :param client: Allows drilling down the TelegramClient instance from the update event.
        """
        if not client:
            session = MemorySession()
            client = TelegramClient(
                session,
                core_settings.telegram_app_id,
                core_settings.telegram_app_hash,
            )
        self.client = client

    async def start(self) -> None:
        if self.client.is_connected():
            return
        logger.info("Initiating Telethon connection.")
        await self.client.start(bot_token=core_settings.telegram_bot_token)

    def start_sync(self) -> None:
        if self.client.is_connected():
            return
        self.client.start(bot_token=core_settings.telegram_bot_token)

    async def stop(self) -> None:
        await self.client.disconnect()

    async def get_chat(self, entity: int | str) -> ChatPeerType:
        return await self.client.get_entity(entity)

    async def get_me(self) -> UserPeerType:
        return await self.client.get_me()

    async def get_user(self, telegram_user_id: int) -> UserPeerType:
        return await self.client.get_entity(telegram_user_id)

    async def get_participants(
        self, chat_id: int
    ) -> AsyncGenerator[TelethonUser, None]:
        async for participant in self.client.iter_participants(chat_id):
            yield participant

    async def get_invite_link(self, chat: ChatPeerType) -> ChatInviteExported:
        invite_link = await self.client(
            ExportChatInviteRequest(
                peer=chat,
                title="Gateway invite link",
                request_needed=True,
            )
        )
        return invite_link

    async def revoke_chat_invite(self, chat_id: int, link: str) -> None:
        chat_peer = await self.get_chat(chat_id)
        await self.client(
            EditExportedChatInviteRequest(
                peer=chat_peer,
                link=link,
                revoked=True,
            )
        )

    async def download_profile_photo(
        self,
        entity: Channel,
        target_location: BinaryIO | IO[bytes],
        current_logo_path: str | None = None,
    ) -> str | None:
        """
        Downloads the profile photo of a specified chat entity if it exists and is not up-to-date.
        Handles cases where the chat does not have a photo or when the existing photo is already
        current. If the download occurs, the function returns the new file name of the photo.

        :param entity: The chat entity from which the profile photo is to be downloaded.
        :param target_location: A BytesIO object representing the target location for downloading
            the profile photo.
        :param current_logo_path: The file name of the current logo, used to determine if a
            download is necessary. If None, a download will occur if the entity has a photo.
        :return: The file name of the new profile photo if successfully downloaded, or None if
            no new download occurred.
        """
        if not entity.photo or isinstance(entity.photo, ChatPhotoEmpty):
            logger.debug(f"Chat {entity.id!r} does not have a logo. Skipping")
            return None

        # Adding timestamp allows bypassing the cache of the image to reflect the change
        new_file_name = f"{entity.photo.photo_id}.png"

        if current_logo_path and current_logo_path == new_file_name:
            logger.debug(f"Logo for chat {entity.id} is up-to-date. Skipping download.")
            return None

        await self.client.download_profile_photo(entity, target_location)

        return new_file_name

    async def promote_user(
        self, chat_id: int, telegram_user_id: int, custom_title: str
    ) -> None:
        chat = await self.get_chat(chat_id)
        user = await self.get_user(telegram_user_id)
        await self.client.edit_admin(
            entity=chat,
            user=user,
            is_admin=True,
            title=custom_title,
        )

    async def demote_user(
        self,
        chat_id: int,
        telegram_user_id: int,
    ) -> None:
        chat = await self.get_chat(chat_id)
        user = await self.get_user(telegram_user_id)
        await self.client.edit_admin(
            entity=chat,
            user=user,
            is_admin=False,
        )

    async def kick_chat_member(self, chat_id: int, telegram_user_id: int) -> None:
        chat = await self.get_chat(chat_id)
        user = await self.get_user(telegram_user_id)
        await self.client.kick_participant(chat, user)
        logger.debug(f"User {user.id!r} was kicked from the chat {chat.id!r}.")

    async def approve_chat_join_request(
        self, chat_id: int, telegram_user_id: int
    ) -> None:
        chat = await self.get_chat(chat_id)
        user = await self.get_user(telegram_user_id)
        await self.client(
            HideChatJoinRequestRequest(peer=chat, user_id=user, approved=True)
        )
        logger.debug(f"User {user.id!r} was approved to join the chat {chat.id!r}.")

    async def decline_chat_join_request(
        self, chat_id: int, telegram_user_id: int
    ) -> None:
        chat = await self.get_chat(chat_id)
        user = await self.get_user(telegram_user_id)
        await self.client(
            HideChatJoinRequestRequest(peer=chat, user_id=user, approved=False)
        )
        logger.debug(f"User {user.id!r} was declined to join the chat {chat.id!r}.")

    async def send_message(
        self, chat_id: int, message: str, buttons: list[list[Button]] | None = None
    ) -> None:
        chat = await self.get_chat(chat_id)
        await self.client.send_message(chat, message, buttons=buttons)
        logger.debug(f"Message {message!r} was sent to the chat {chat_id!r}.")
