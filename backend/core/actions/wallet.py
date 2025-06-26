import logging

from celery.result import AsyncResult
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy.orm import Session

from core.actions.authorization import AuthorizationAction
from core.dtos.wallet import WalletDetailsWithProofDTO
from core.actions.base import BaseAction
from core.constants import (
    DEFAULT_WALLET_TRACK_EXPIRATION,
    CELERY_WALLET_FETCH_QUEUE_NAME,
)
from core.exceptions.chat import TelegramChatNotExists
from core.models.chat import TelegramChat
from core.services.chat import TelegramChatService
from core.services.chat.user import TelegramChatUserService
from core.services.superredis import RedisService
from core.services.ton import TonProofService
from core.services.user import UserService
from core.services.wallet import (
    WalletService,
    TelegramChatUserWalletService,
)
from core.exceptions.wallet import (
    UserWalletConnectedAnotherUserError,
    UserWalletNotConnectedError,
    UserWalletConnectedError,
)
from indexer.celery_app import app

logger = logging.getLogger(__name__)


class WalletAction(BaseAction):
    def __init__(self, db_session: Session):
        super().__init__(db_session)
        self.wallet_service = WalletService(db_session)
        self.telegram_chat_service = TelegramChatService(db_session)
        self.telegram_chat_user_service = TelegramChatUserService(db_session)
        self.telegram_chat_user_wallet_service = TelegramChatUserWalletService(
            db_session
        )
        self.user_service = UserService(db_session)

    async def connect_wallet(
        self,
        user_id: int,
        chat_slug: str,
        wallet_details: WalletDetailsWithProofDTO,
    ) -> str:
        """
        Connects a wallet to a user and associates it with a Telegram chat. This method performs
        several checks such as verifying the wallet's Ton proof, ensuring the wallet isn't already
        linked to a different user, and validating the existence of the Telegram chat. Additionally,
        it initiates wallet data loading, updates tracking for the wallet, and handles synchronization
        with Redis services.

        :param user_id: The unique identifier of the user to whom the wallet is being connected.
        :param chat_slug: The slug identifier representing the Telegram chat.
        :param wallet_details: An object containing wallet address and its associated proof for
            verification purposes.
        :return: A string representing the task ID of the asynchronous operation for initial wallet
            data loading on reconnect.
        :raises UserWalletConnectedAnotherUserError: If the wallet is already connected to a different user.
        :raises TelegramChatNotExists: If no Telegram chat exists with the provided slug identifier.
        :raises UserWalletConnectedError: If the wallet is already connected to the specified chat.
        """
        TonProofService.verify_ton_proof(wallet_details=wallet_details)

        connected_wallet = self.wallet_service.get_user_wallet(
            wallet_details.wallet_address
        )
        if connected_wallet and connected_wallet.user_id != user_id:
            raise UserWalletConnectedAnotherUserError(
                f"Wallet {wallet_details.wallet_address!r} already connected to another user"
            )

        try:
            chat = self.telegram_chat_service.get_by_slug(chat_slug)
        except NoResultFound:
            raise TelegramChatNotExists(f"Chat {chat_slug!r} not found")

        if not connected_wallet:
            self.wallet_service.connect_user_wallet(
                user_id=user_id,
                wallet_address=wallet_details.wallet_address,
            )

        same_wallet_connected = False
        try:
            self._set_wallet(
                user_id=user_id,
                chat_id=chat.id,
                wallet_address=wallet_details.wallet_address,
            )
        except UserWalletConnectedError:
            # Allow reconnecting already connected wallet and trigger indexing
            same_wallet_connected = True

        if not connected_wallet:
            # Add wallet to tracking if it was not connected before
            redis_external_service = RedisService(external=True)
            redis_external_service.set(
                key=wallet_details.wallet_address,
                value="",
                ex=DEFAULT_WALLET_TRACK_EXPIRATION,
            )

        redis_service = RedisService()
        cache_set = redis_service.set(
            key=f"wallet-details-{wallet_details.wallet_address}",
            value="1",
            # Only allow manual indexing once a minute
            ex=60,
            nx=True,
        )
        task_result: AsyncResult | None = None
        if cache_set:
            # Run initial wallet data loading
            task_result = app.send_task(
                "fetch-wallet-details",
                args=(wallet_details.wallet_address,),
                queue=CELERY_WALLET_FETCH_QUEUE_NAME,
            )
        else:
            logger.warning(
                f"Wallet {wallet_details.wallet_address!r} was already indexed over this minute. Skipping initial indexing."
            )

        if not same_wallet_connected:
            await self.on_wallet_reconnect(
                chat=chat,
                user_id=user_id,
                is_disconnecting=False,
            )

        logger.info(
            f"User {user_id!r} linked wallet {wallet_details.wallet_address!r} to the chat {chat.id!r}"
        )
        return task_result.task_id if task_result else None

    async def on_wallet_reconnect(
        self, chat: TelegramChat, user_id: int, is_disconnecting: bool
    ) -> None:
        """
        Handles wallet reconnection for a user in a Telegram chat. This method checks if a
        user is an eligible member of the chat upon reconnection. If the user is not eligible
        and is present in the chat, they are kicked and removed.

        :param chat: TelegramChat instance representing the chat where the user is being
                     re-evaluated for membership.
        :param user_id: Unique identifier for the user being reconnected.
        :param is_disconnecting: A flag indicating whether the wallet action relates to
                                 disconnecting or connecting. If True, wallet checks
                                 are skipped during eligibility evaluations.
        """
        try:
            telegram_chat_user = self.telegram_chat_user_service.get(
                chat_id=chat.id,
                user_id=user_id,
            )
        except NoResultFound:
            logger.debug(
                f"User {user_id!r} is not a chat member for {chat.id!r}. Skipping."
            )
            return

        logger.info(
            f"User {user_id!r} is a chat member for {chat.id!r}. Checking permissions."
        )
        authorization_action = AuthorizationAction(db_session=self.db_session)
        is_eligible = authorization_action.is_user_eligible_chat_member(
            user_id=user_id, chat_id=chat.id, check_wallet=not is_disconnecting
        )
        if not is_eligible:
            logger.info(
                f"User {user_id!r} is not eligible for chat {chat.id!r}. Kicking."
            )
            await authorization_action.kick_chat_member(telegram_chat_user)

    async def disconnect_wallet(self, user_id: int, chat_slug: str) -> None:
        """
        Disconnects a wallet associated with a user from a specific Telegram chat. If the chat
        with the given chat_slug does not exist, an exception is raised. This method also performs a
        cleanup by removing the wallet mapping and updating the Redis set to reflect the disconnected
        status. Finally, it logs the operation for tracking purposes.

        WARNING: It doesn't remove the UserWallet link

        :param user_id: The unique identifier of the user whose wallet needs to be disconnected.
        :param chat_slug: The unique slug identifier of the Telegram chat from which the user's wallet
            is being disconnected.
        :raises TelegramChatNotExists: If no chat exists with the provided slug identifier.
        """
        try:
            chat = self.telegram_chat_service.get_by_slug(chat_slug)
        except NoResultFound:
            raise TelegramChatNotExists(f"Chat {chat_slug!r} not found")

        await self.on_wallet_reconnect(
            chat=chat,
            user_id=user_id,
            is_disconnecting=True,
        )

        # Remove user wallet mapping
        self.telegram_chat_user_wallet_service.disconnect(
            chat_id=chat.id,
            user_id=user_id,
        )

        logger.info(f"User {user_id!r} disconnected wallet from chat {chat.id!r}")

    def _set_wallet(
        self,
        user_id: int,
        chat_id: int,
        wallet_address: str,
    ) -> None:
        """
        Sets or updates the wallet connection for a user in a specific chat. If the specified wallet is already
        connected to the given chat by the user, it raises an error. If any previously connected wallet exists,
        it disconnects it before proceeding to connect the new wallet.

        :param user_id: Identifier of the user attempting to connect a wallet.
        :param chat_id: Identifier of the chat where the wallet will be connected.
        :param wallet_address: The unique wallet address to be connected with the user and chat.

        :raises UserWalletConnectedError: If the wallet is already connected to the specified chat.

        """
        try:
            connected_chat_wallet = self.telegram_chat_user_wallet_service.get(
                user_id=user_id, chat_id=chat_id
            )
            if wallet_address == connected_chat_wallet.address:
                logger.warning(
                    f"User {user_id!r} tried to connect wallet {wallet_address!r} to the chat {chat_id!r} "
                    f"that was already connected by user. Ignoring."
                )
                raise UserWalletConnectedError(
                    f"Wallet {wallet_address!r} was already connected by user"
                )
        except NoResultFound:
            logger.debug(
                f"User {user_id!r} has no wallet connected to chat {chat_id!r}. Ignoring."
            )
            connected_chat_wallet = None

        if connected_chat_wallet:
            self.telegram_chat_user_wallet_service.disconnect(
                user_id=user_id,
                chat_id=chat_id,
            )

        try:
            # Connect new wallet only if it was not connected before
            self.telegram_chat_user_wallet_service.connect(
                user_id=user_id,
                chat_id=chat_id,
                wallet_address=wallet_address,
            )
        except IntegrityError:
            logger.warning(
                f"User {user_id!r} tried to connect wallet {wallet_address!r} to the chat {chat_id!r} "
                f"that was already connected by user (was not detected on the first check). Ignoring."
            )
            raise UserWalletConnectedError(
                f"Wallet {wallet_address!r} was already connected by user"
            )

        logger.info(
            f"User {user_id!r} set wallet {wallet_address!r} for chat {chat_id!r}"
        )

    async def set_wallet(
        self, user_id: int, chat_slug: str, wallet_address: str
    ) -> None:
        """
        Sets a wallet for a user in a specified chat by connecting the wallet address to the
        user within the chat.

        This method handles the process of associating a wallet address with a user for a
        specific Telegram chat. It validates whether the wallet address is already connected
        to the user. If the specified chat does not exist, it raises an exception. Once the
        validations pass, the wallet is successfully connected, and a record of the action
        is logged.

        :param user_id: The unique identifier of the user.
        :param chat_slug: The unique slug identifier of the chat.
        :param wallet_address: The wallet address to be set for the user.

        :raises TelegramChatNotExists: If no chat exists with the provided slug identifier.
        :raises UserWalletNotConnectedError: If the wallet is already connected to the specified chat.
        """
        try:
            chat = self.telegram_chat_service.get_by_slug(chat_slug)
        except NoResultFound:
            raise TelegramChatNotExists(f"Chat {chat_slug!r} not found")

        connected_wallet = self.wallet_service.get_user_wallet(
            wallet_address=wallet_address, user_id=user_id
        )
        if not connected_wallet:
            logger.warning(
                f"User {user_id!r} tried to connect wallet {wallet_address!r} that wasn't connected by user. Ignoring."
            )
            raise UserWalletNotConnectedError(
                f"Wallet {wallet_address!r} was not connected by user"
            )

        self._set_wallet(
            user_id=user_id,
            chat_id=chat.id,
            wallet_address=wallet_address,
        )
