import logging

from sqlalchemy.orm import Session

from community_manager.dtos.chat import TargetChatMembersDTO
from community_manager.entrypoint import init_client
from community_manager.settings import community_manager_settings
from core.actions.authorization import AuthorizationAction
from core.constants import UPDATED_WALLETS_SET_NAME, UPDATED_STICKERS_USER_IDS
from core.services.chat.rule.sticker import TelegramChatStickerCollectionService
from core.services.chat.user import TelegramChatUserService
from core.services.superredis import RedisService
from core.services.user import UserService

logger = logging.getLogger(__name__)


class CommunityManagerChatAction:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.user_service = UserService(db_session)
        self.telegram_chat_user_service = TelegramChatUserService(db_session)
        self.telegram_chat_sticker_collection_service = (
            TelegramChatStickerCollectionService(db_session)
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

        target_chat_members: set[tuple[int, int]] = set()

        if wallets:
            chat_members = self.telegram_chat_user_service.get_all_by_linked_wallet(
                addresses=wallets
            )
            target_chat_members.update(
                {(cm.chat_id, cm.user_id) for cm in chat_members}
            )

        if sticker_owners_telegram_ids:
            rules = self.telegram_chat_sticker_collection_service.get_all(
                enabled_only=True
            )
            unique_chat_ids = {r.chat_id for r in rules}
            users = self.user_service.get_all(telegram_ids=sticker_owners_telegram_ids)
            chat_members = self.telegram_chat_user_service.get_all(
                user_ids=[user.id for user in users],
                chat_ids=list(unique_chat_ids),
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
            sticker_owners_ids=sticker_owners_telegram_ids,
            target_chat_members=target_chat_members,
        )

    async def sanity_chat_checks(self) -> None:
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

                telethon_service = init_client()
                authorization_action = AuthorizationAction(
                    self.db_session, telethon_client=telethon_service.client
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
        self.redis_service.add_to_set(UPDATED_WALLETS_SET_NAME, *dto.wallets)
        self.redis_service.add_to_set(
            UPDATED_STICKERS_USER_IDS, *map(str, dto.sticker_owners_ids)
        )
