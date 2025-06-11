import asyncio
import logging
from pathlib import Path
from typing import AsyncGenerator, IO, BinaryIO

from telethon import TelegramClient, Button
from telethon.errors import MultiError, FloodWaitError, RPCError
from telethon.sessions import MemorySession, SQLiteSession
from telethon.tl.functions.messages import (
    ExportChatInviteRequest,
    HideChatJoinRequestRequest,
    EditExportedChatInviteRequest,
    GetCustomEmojiDocumentsRequest,
    GetStickerSetRequest,
)
from telethon.tl.functions.payments import (
    GetUniqueStarGiftRequest,
    GetSavedStarGiftsRequest,
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
    StarGiftUnique,
    Document,
    DocumentAttributeCustomEmoji,
    StickerSet,
    DocumentAttributeFilename,
)
from telethon.tl.types.payments import SavedStarGifts

from core.constants import DEFAULT_TELEGRAM_BATCH_PROCESSING_SIZE
from core.settings import core_settings

logger = logging.getLogger(__name__)


ChatPeerType = Channel | InputPeerChat | InputPeerChannel
UserPeerType = TelethonUser | InputPeerUser | InputUser


class TelethonService:
    def __init__(
        self,
        client: TelegramClient | None = None,
        session_path: Path | None = None,
        bot_token: str | None = None,
    ) -> None:
        """
        Initializes the Telegram bot client with a given Telegram client instance or creates one
        using the provided session path or an in-memory session.
        The bot token is used for authentication if provided.
        This class facilitates interaction with the Telegram API.

        :param client: An instance of `TelegramClient`.
            If None, a new client instance is created.
        :param session_path: Path to the session file for the Telegram client.
            If None, an in-memory session is used.
        :param bot_token: The token string for the Telegram bot.
            If provided, the client authenticates using this token.
        """
        if not client:
            if session_path:
                session = SQLiteSession(str(session_path))
            else:
                session = MemorySession()
            client = TelegramClient(
                session,
                core_settings.telegram_app_id,
                core_settings.telegram_app_hash,
            )
        self.client = client
        self.bot_token = bot_token

    async def start(self) -> None:
        """
        Initiates the connection process for the Telethon client.

        This method checks if the client is already connected. If not, it begins
        the connection process. Depending on whether a bot token is provided, it
        will either start a bot session or a user session. Logs information about
        the initiation process.

        :raises Exception: May propagate exceptions raised during the connection
            initiation process.
        """
        if self.client.is_connected():
            return

        logger.info("Initiating Telethon connection.")
        if self.bot_token:
            await self._start_bot_session()
        else:
            await self._start_session()

    async def _start_bot_session(self) -> None:
        """
        Starts the bot session using the provided bot token.

        This method initializes the bot session by starting the client with the
        specific bot token.
        """
        await self.client.start(bot_token=self.bot_token)

    async def _start_session(self) -> None:
        """
        Starts a Telegram client session asynchronously.

        This internal method initializes the session by invoking the Telethon client's
        start method.
        It provides a placeholder phone number to bypass the actual authentication requirement,
        as signup is not supported by Telethon.
        Therefore, it requires a session to be initialized prior to this method execution.
        """
        # Setting the wrong number on purpose as signup is not supported by Telethon
        # https://github.com/LonamiWebs/Telethon/issues/4050
        await self.client.start(phone=lambda: "+888")

    def start_sync(self) -> None:
        if self.client.is_connected():
            return

        if not self.bot_token:
            raise ValueError("Bot token is required for synchronous connection.")

        self.client.start(bot_token=self.bot_token)

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

    async def download_unique_gift_thumbnail(
        self,
        entity: StarGiftUnique,
        target_location: BinaryIO | IO[bytes],
    ) -> str:
        """
        Download the thumbnail of a unique gift and save it to the specified location.

        This asynchronous method facilitates downloading the preview thumbnail
        of a unique gift from a source entity and saving it to the defined target
        location.
        Upon successful download, it returns the generated filename of
        the thumbnail, which is constructed based on the unique gift's slug name.

        :param entity: The unique star gift entity whose thumbnail is to be downloaded.
                       It contains attributes that provide the necessary document
                       data required for the download operation.
        :param target_location: A binary file-like object representing the destination
                                where the thumbnail is to be written. It can be any
                                object that adheres to the BinaryIO or IO[bytes] type.
        :return: The filename of the downloaded thumbnail, derived from the slug
                 of the input entity with a "-preview.png" suffix.
        """
        await self.client.download_media(
            message=entity.attributes[0].document, file=target_location, thumb=0
        )
        return f"{entity.slug}-preview.png"

    async def download_emoji(
        self,
        emoji: Document,
        target_location: BinaryIO | IO[bytes],
    ) -> str:
        """
        Download the emoji document and save it to the specified location.
        """
        filename = next(
            filter(lambda a: isinstance(a, DocumentAttributeFilename), emoji.attributes)
        ).file_name
        suffix = Path(filename).suffix
        await self.client.download_media(
            message=emoji,
            file=target_location,  # type: ignore
        )
        return f"{emoji.id}{suffix}"

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

    async def index_emoji(self, emoji_id: int) -> tuple[Document, StickerSet]:
        """
        Indexes a custom emoji based on its unique identifier and retrieves its associated
        sticker set. This function queries the Telegram API to fetch the emoji document
        and its sticker set details. If more than one emoji document is returned, an
        error is raised to ensure exactly one emoji is processed.

        :param emoji_id: The unique identifier of the emoji to be indexed.
        :return: A tuple containing the emoji document and the corresponding sticker
            set details.
        :raises ValueError: If the number of emoji documents returned is not exactly one.
        """
        emojis = await self.client(
            GetCustomEmojiDocumentsRequest(document_id=[emoji_id])
        )
        if len(emojis) != 1:
            logger.error(
                f"Expected exactly one emoji, got {len(emojis)}: {[e.stringify() for e in emojis]}"
            )
            raise ValueError(f"Expected exactly one emoji, got {len(emojis)}")

        emoji = emojis[0]
        sticker_set_input = next(
            filter(
                lambda a: isinstance(a, DocumentAttributeCustomEmoji), emoji.attributes
            )
        ).stickerset
        sticker_set = await self.client(
            GetStickerSetRequest(stickerset=sticker_set_input, hash=0)
        )
        logger.info(
            f"Indexed emoji {emoji.id!r} and sticker set {sticker_set.set.id!r}."
        )
        return emoji, sticker_set.set

    async def index_gift(self, slug: str, number: int) -> StarGiftUnique:
        """
        Asynchronously retrieves unique star gift data by combining the provided slug and
        number into a specific identifier.
        This function interfaces with an external API client to fetch the requested star gift
        and returns the corresponding unique gift object.

        :param slug: The unique string identifier part of the gift.
        :param number: The numeric identifier part to combine with the slug.
        :return: The unique star gift associated with the computed identifier.
        :rtype: StarGiftUnique
        """
        gift = await self.client(GetUniqueStarGiftRequest(slug=f"{slug}-{number}"))
        return gift.gift

    async def index_gifts_batch(
        self,
        slugs: list[str],
    ) -> list[StarGiftUnique]:
        """
        Indexes a batch of gifts by processing a list of slugs.

        Each slug is used to make a request to retrieve the corresponding unique star gifts.
        The method ensures that any MultiError exceptions encountered are handled to
        extract valid responses, and returns a list of unique star gifts based on
        valid fetched data.

        More info: https://docs.telethon.dev/en/stable/concepts/full-api.html#requests-in-parallel

        :param slugs: A list of slug strings used to fetch unique star gifts.
        :return: A list of StarGiftUnique objects that correspond to the provided
            slugs.
        """
        try:
            gifts = await self.client(
                [GetUniqueStarGiftRequest(slug=slug) for slug in slugs],
                # ordered=True # There is a way to run them ordered, but we don't really care about the order
            )
        except MultiError as e:
            logger.error(f"Error occurred while fetching gifts: {e}")
            if any((isinstance(exc, FloodWaitError) for exc in e.exceptions)):
                # Typical Flood timeout for gifts fetching is 3 seconds
                # We can go forward, but there is a chance of get banned or lose some data because of the errors
                logger.warning(
                    f"FloodWaitError occurred while fetching gifts: {e.exceptions[0]}. Waiting for 3 seconds."
                )
                await asyncio.sleep(3.1)

            gifts = [r for r in e.results if r]
            logger.warning(
                f"Received {len(gifts)} gifts from the API out of {len(slugs)} requested."
            )
        except RPCError as e:
            # If there is only one item left – it'll raise an RPCError instead of MultiError
            logger.error(f"Error occurred while fetching gift: {e}")
            gifts = []

        return [gift.gift for gift in gifts if isinstance(gift.gift, StarGiftUnique)]

    async def index_user_gifts(
        self,
        telegram_user_id: int,
        batch_limit: int = DEFAULT_TELEGRAM_BATCH_PROCESSING_SIZE,
    ) -> list[StarGiftUnique]:
        """
        Indexes all the unique gifts associated with a specified Telegram user by
        retrieving them in batches.
        The function proceeds iteratively, fetching a batch of gifts at a time,
        until no more gifts remain to be processed.

        :param telegram_user_id: The unique identifier representing a Telegram user.
        :param batch_limit: The maximum number of gifts to retrieve in each batch.

        :return: A list of unique StarGift objects associated with the Telegram user.
        """
        all_gifts = []
        # The Default offset is zero, meaning it should start from the very beginning
        next_offset = "0"
        while next_offset:
            saved_gifts = await self._index_user_gifts_batch(
                user=await self.get_user(telegram_user_id),
                offset=next_offset,
                limit=batch_limit,
            )
            all_gifts.extend(
                [
                    sg.gift
                    for sg in saved_gifts.gifts
                    if isinstance(sg.gift, StarGiftUnique)
                ]
            )
            next_offset = saved_gifts.next_offset

        return all_gifts

    async def _index_user_gifts_batch(
        self,
        user: UserPeerType,
        offset: str,
        limit: int,
    ) -> SavedStarGifts:
        """
        Indexes a batch of user gifts by retrieving saved star gifts based on the provided
        user peer type, offset, and limit.
        This asynchronous function sends a request to fetch the gifts' data from the server.

        :param user: The user peer identifying the user for whom the gifts are being
            indexed.
        :param offset: The pagination offset to determine the starting point of the
            batch retrieval.
        :param limit: The number of gifts to retrieve in the batch.
        :return: A collection of saved star gifts for the user corresponding to the
            given offset and limit.
        """
        return await self.client(
            GetSavedStarGiftsRequest(peer=user, offset=offset, limit=limit)
        )
