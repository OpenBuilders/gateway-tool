import logging
from collections import defaultdict

from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from telethon import TelegramClient
from telethon.errors import (
    UserAdminInvalidError,
    RPCError,
)

from core.actions.base import BaseAction
from core.dtos.chat.rule import (
    TelegramChatEligibilityRulesDTO,
)
from core.enums.rule import EligibilityCheckType
from core.dtos.chat.rule.internal import (
    EligibilitySummaryInternalDTO,
    RulesEligibilitySummaryInternalDTO,
    RulesEligibilityGroupSummaryInternalDTO,
    EligibilitySummaryGiftCollectionInternalDTO,
    EligibilitySummaryStickerCollectionInternalDTO,
    EligibilitySummaryJettonInternalDTO,
    EligibilitySummaryNftCollectionInternalDTO,
)
from core.dtos.gift.collection import GiftCollectionDTO
from core.dtos.resource import JettonDTO, NftCollectionDTO
from core.dtos.sticker import MinimalStickerCollectionDTO, MinimalStickerCharacterDTO
from core.enums.nft import NftCollectionAsset
from core.exceptions.telethon import MissingChatEntityError, MissingUserEntityError
from core.models import GiftUnique
from core.models.blockchain import NftItem
from core.models.chat import (
    TelegramChatUser,
)
from core.models.rule import TelegramChatWhitelistExternalSource, TelegramChatWhitelist
from core.models.sticker import StickerItem
from core.models.user import User
from core.models.wallet import JettonWallet, UserWallet
from core.services.chat import TelegramChatService
from core.services.chat.rule.blockchain import (
    TelegramChatJettonService,
    TelegramChatNFTCollectionService,
    TelegramChatToncoinService,
)
from core.services.chat.rule.emoji import TelegramChatEmojiService
from core.services.chat.rule.gift import TelegramChatGiftCollectionService
from core.services.chat.rule.premium import TelegramChatPremiumService
from core.services.chat.rule.sticker import TelegramChatStickerCollectionService
from core.services.chat.rule.whitelist import (
    TelegramChatExternalSourceService,
    TelegramChatWhitelistService,
)
from core.services.chat.user import TelegramChatUserService
from core.services.gift.item import GiftUniqueService
from core.services.nft import NftItemService
from core.services.sticker.item import StickerItemService
from core.services.supertelethon import TelethonService
from core.services.wallet import JettonWalletService, TelegramChatUserWalletService
from core.settings import core_settings
from core.utils.gift import find_relevant_gift_items
from core.utils.nft import find_relevant_nft_items
from core.utils.sticker import find_relevant_sticker_items

logger = logging.getLogger(__name__)


class AuthorizationAction(BaseAction):
    """
    Actions related to user authorization in the chat

    This is the only low-level action that could be used in the high-level actions
    """

    def __init__(
        self, db_session: Session, telethon_client: TelegramClient | None = None
    ) -> None:
        super().__init__(db_session)
        self.jetton_wallet_service = JettonWalletService(db_session)
        self.telegram_chat_user_service = TelegramChatUserService(db_session)
        self.telegram_chat_user_wallet_service = TelegramChatUserWalletService(
            db_session
        )
        self.telegram_chat_toncoin_service = TelegramChatToncoinService(db_session)
        self.telegram_chat_jetton_service = TelegramChatJettonService(db_session)
        self.telegram_chat_nft_collection_service = TelegramChatNFTCollectionService(
            db_session
        )
        self.telegram_chat_external_source_service = TelegramChatExternalSourceService(
            db_session
        )
        self.telegram_chat_whitelist_group_service = TelegramChatWhitelistService(
            db_session
        )
        self.telegram_chat_premium_service = TelegramChatPremiumService(db_session)
        self.telegram_chat_sticker_collection_service = (
            TelegramChatStickerCollectionService(db_session)
        )
        self.telegram_chat_emoji_service = TelegramChatEmojiService(db_session)
        self.telegram_chat_gift_collection_service = TelegramChatGiftCollectionService(
            db_session
        )
        self.telethon_service = TelethonService(
            client=telethon_client, bot_token=core_settings.telegram_bot_token
        )

    def is_user_eligible_chat_member(
        self, user_id: int, chat_id: int, check_wallet: bool = True
    ) -> RulesEligibilitySummaryInternalDTO:
        """
        Determines whether a user is eligible to be a chat member based on the eligibility
        rules associated with the specified chat.

        The function checks the eligibility of a user by verifying their associated NFT items,
        jetton balances, and any specific eligibility rules tied to the chat.

        :param user_id: The unique identifier of the user.
        :param chat_id: The unique identifier of the chat where eligibility
                        is being evaluated.
        :param check_wallet: Whether the wallet should be checked
                        (e.g. if the user disconnects the wallet and eligibility after that action has to be checked)
                        If set to false, wallet-related rules will be skipped.
        :return: An internal data object summarizing the user's eligibility based
                 on the chat-specific rules.
        """
        user = self.user_service.get(user_id=user_id)
        telegram_chat_user = self.telegram_chat_user_service.find(
            chat_id=chat_id, user_id=user.id
        )
        eligibility_rules = self.get_eligibility_rules(chat_id=chat_id)

        user_wallet: UserWallet | None = None
        user_nft_items = []
        user_jettons = []

        if check_wallet:
            nft_item_service = NftItemService(self.db_session)
            try:
                user_wallet: UserWallet = self.telegram_chat_user_wallet_service.get(
                    user_id=user.id, chat_id=chat_id
                ).wallet
                if eligibility_rules.nft_collections:
                    user_nft_items = nft_item_service.get_all(
                        owner_address=user_wallet.address
                    )
                else:
                    user_nft_items = []

                if eligibility_rules.jettons:
                    user_jettons = self.jetton_wallet_service.get_all(
                        owner_address=user_wallet.address
                    )
                else:
                    user_jettons = []

            except NoResultFound:
                logger.debug(
                    f"User {user.id} doesn't have a connected wallet. Skipping."
                )

        if eligibility_rules.stickers:
            sticker_item_service = StickerItemService(self.db_session)
            user_sticker_items = sticker_item_service.get_all(
                telegram_user_id=user.telegram_id
            )
        else:
            user_sticker_items = []

        if eligibility_rules.gifts:
            gift_unique_service = GiftUniqueService(self.db_session)
            user_gift_unique_items = gift_unique_service.get_all(
                telegram_user_id=user.telegram_id
            )
        else:
            user_gift_unique_items = []

        eligibility_summary = self.check_chat_member_eligibility(
            eligibility_rules=eligibility_rules,
            user=user,
            user_wallet=user_wallet,
            user_jettons=user_jettons,
            user_nft_items=user_nft_items,
            user_sticker_items=user_sticker_items,
            user_gift_items=user_gift_unique_items,
            chat_member=telegram_chat_user,
        )
        return eligibility_summary

    def get_eligibility_rules(
        self, chat_id: int, enabled_only: bool = True
    ) -> TelegramChatEligibilityRulesDTO:
        """
        Get eligibility rules for the chat based on the database records
        :param chat_id: Chat ID for which the rules are to be fetched
        :param enabled_only: Fetch only enabled rules. Set to False if you request rules for management purposes
        :return: Eligibility rules for the chat
        """
        all_toncoin_rules = self.telegram_chat_toncoin_service.get_all(
            chat_id, enabled_only=enabled_only
        )
        all_jetton_rules = self.telegram_chat_jetton_service.get_all(
            chat_id, enabled_only=enabled_only
        )
        all_nft_collections = self.telegram_chat_nft_collection_service.get_all(
            chat_id, enabled_only=enabled_only
        )
        all_external_source_rules = self.telegram_chat_external_source_service.get_all(
            chat_id, enabled_only=enabled_only
        )
        all_whitelist_groups = self.telegram_chat_whitelist_group_service.get_all(
            chat_id, enabled_only=enabled_only
        )
        all_premium_rules = self.telegram_chat_premium_service.get_all(
            chat_id, enabled_only=enabled_only
        )
        all_emoji_rules = self.telegram_chat_emoji_service.get_all(
            chat_id, enabled_only=enabled_only
        )
        all_sticker_rules = self.telegram_chat_sticker_collection_service.get_all(
            chat_id, enabled_only=enabled_only
        )
        all_gift_rules = self.telegram_chat_gift_collection_service.get_all(
            chat_id, enabled_only=enabled_only
        )
        return TelegramChatEligibilityRulesDTO(
            toncoin=all_toncoin_rules,
            jettons=all_jetton_rules,
            stickers=all_sticker_rules,
            gifts=all_gift_rules,
            nft_collections=all_nft_collections,
            whitelist_external_sources=all_external_source_rules,
            whitelist_sources=all_whitelist_groups,
            premium=all_premium_rules,
            emoji=all_emoji_rules,
        )

    def get_ineligible_chat_members(
        self,
        chat_members: list[TelegramChatUser],
    ) -> list[TelegramChatUser]:
        """
        Determines and returns a list of chat members who are ineligible to be part of their respective chats based on
        eligibility rules and various related data sources such as wallets, NFTs, and gifts. This functionality checks
        each member's eligibility against the chat's specific rules, wallet information, NFTs, jettons, stickers, and
        other items associated with the user. Users that do not meet the criteria defined by the chat's eligibility
        rules are considered ineligible.

        :param chat_members: A list of TelegramChatUser objects representing the members of various Telegram chats.
        :return: A list of TelegramChatUser objects representing chat members who are not eligible to be part of their
            respective chats.
        """
        members_per_chat = defaultdict(list)
        user_id_to_telegram_id = {}
        eligibility_rules_per_chat: dict[int, TelegramChatEligibilityRulesDTO] = {}

        chat_members = [
            # Skip checks for non-managed users in the chats where full control is disabled
            chat_member
            for chat_member in chat_members
            if chat_member.chat.is_full_control or chat_member.is_managed
        ]

        if not chat_members:
            logger.info("No chat members to check eligibility for. Skipping.")
            return []

        for chat_member in chat_members:
            members_per_chat[chat_member.chat_id].append(chat_member)
            eligibility_rules_per_chat[
                chat_member.chat_id
            ] = self.get_eligibility_rules(chat_id=chat_member.chat_id)
            user_id_to_telegram_id[chat_member.user_id] = chat_member.user.telegram_id

        nft_item_service = NftItemService(self.db_session)

        unique_wallets: set[tuple[int, str]] = {
            (chat_member.user_id, chat_member.wallet_link.address)
            for chat_member in chat_members
            # Some users might don't have the wallet connected,
            #  but are still chat members
            if chat_member.wallet_link
        }

        nft_items_per_wallet = defaultdict(list)
        jetton_wallets_per_wallet = defaultdict(list)
        sticker_items_per_user = {}
        gift_items_per_user = {}

        sticker_item_service = StickerItemService(self.db_session)
        gift_unique_service = GiftUniqueService(self.db_session)

        # Prefetch wallet resources from the database
        for user_id, wallet in unique_wallets:
            nft_items_per_wallet[wallet] = nft_item_service.get_all(
                owner_address=wallet
            )
            jetton_wallets_per_wallet[wallet] = self.jetton_wallet_service.get_all(
                owner_address=wallet
            )
            # Users could be repeated if one user has multiple wallets connected
            if user_id not in sticker_items_per_user:
                sticker_items_per_user[user_id] = sticker_item_service.get_all(
                    telegram_user_id=user_id_to_telegram_id[user_id]
                )
            if user_id not in gift_items_per_user:
                gift_items_per_user[user_id] = gift_unique_service.get_all(
                    telegram_user_id=user_id_to_telegram_id[user_id]
                )

        ineligible_members = []
        for chat, members in members_per_chat.items():
            for member in members:
                member_wallet = (
                    member.wallet_link.wallet if member.wallet_link else None
                )
                member_wallet_address = member_wallet.address if member_wallet else None
                if not (
                    eligibility_summary := self.check_chat_member_eligibility(
                        eligibility_rules=eligibility_rules_per_chat[chat],
                        user=member.user,
                        user_wallet=member_wallet,
                        user_jettons=jetton_wallets_per_wallet.get(
                            member_wallet_address, []
                        ),
                        user_nft_items=nft_items_per_wallet.get(
                            member_wallet_address, []
                        ),
                        user_sticker_items=sticker_items_per_user.get(
                            member.user_id, []
                        ),
                        user_gift_items=gift_items_per_user.get(member.user_id, []),
                        chat_member=member,
                    )
                ):
                    logger.debug(
                        f"User {member.user.telegram_id!r} is not eligible to be in chat {chat!r}."
                        f"Eligibility summary: {eligibility_summary!r}"
                    )
                    ineligible_members.append(member)

        return ineligible_members

    @classmethod
    def check_chat_member_eligibility(
        cls,
        eligibility_rules: TelegramChatEligibilityRulesDTO,
        user: User,
        user_wallet: UserWallet | None,
        user_jettons: list[JettonWallet],
        user_nft_items: list[NftItem],
        user_sticker_items: list[StickerItem],
        user_gift_items: list[GiftUnique],
        chat_member: TelegramChatUser | None = None,
    ) -> RulesEligibilitySummaryInternalDTO:
        """
        Analyzes a Telegram chat member's eligibility based on a set of predefined rules,
        including jetton balances, owned NFTs, whitelist memberships, and external source
        validations. This method aggregates the eligibility information and returns a
        summary of the assessment.

        :param eligibility_rules: A data object containing the eligibility conditions,
            including requirements for jetton balances, NFT collections, whitelist memberships,
            and other external sources.
        :param user: The Telegram chat user whose eligibility is being evaluated.
        :param user_wallet: The wallet linked by the user to the requested chat.
        :param user_jettons: A list of user's jetton wallets containing balance and
            related information.
        :param user_nft_items: A list of user's NFT items collected, which are checked
            against required NFT eligibility rules.
        :param user_sticker_items: A list of user's sticker items collected, which are checked
        :param user_gift_items: A list of user's gift unique items collected, which are checked
        :param chat_member: Optional parameter representing the Telegram chat member.
            Includes attributes such as admin status in the chat.
        :return: A detailed summary encapsulating the carried-out eligibility checks,
            including specific details for each eligibility rule (jetton, NFT, whitelist,
            external source). Also includes information about the user's admin status in
            the chat if applicable.
        """
        items = []
        user_jettons_by_master_address = {
            jetton_wallet.jetton_master_address: jetton_wallet
            for jetton_wallet in user_jettons
        }
        # Check if the user has the required toncoin balance
        items.extend(
            [
                EligibilitySummaryInternalDTO(
                    id=rule.id,
                    group_id=rule.group_id,
                    type=EligibilityCheckType.TONCOIN,
                    category=rule.category,
                    expected=rule.threshold,
                    title="TON",
                    actual=(user_wallet.balance if user_wallet else None) or 0,
                    is_enabled=rule.is_enabled,
                )
                for rule in eligibility_rules.toncoin
            ]
        )
        # Check if the user has all required jetton balances
        items.extend(
            [
                EligibilitySummaryJettonInternalDTO(
                    id=rule.id,
                    group_id=rule.group_id,
                    type=EligibilityCheckType.JETTON,
                    category=rule.category,
                    expected=rule.threshold,
                    title=rule.jetton.name,
                    address_raw=rule.address,
                    actual=(
                        user_jetton_wallet.balance
                        if (
                            user_jetton_wallet := user_jettons_by_master_address.get(
                                rule.address
                            )
                        )
                        else 0
                    ),
                    is_enabled=rule.is_enabled,
                    jetton=JettonDTO.from_orm(rule.jetton),
                )
                for rule in eligibility_rules.jettons
            ]
        )
        # Check if the user has all required NFT items
        items.extend(
            [
                EligibilitySummaryNftCollectionInternalDTO(
                    id=rule.id,
                    group_id=rule.group_id,
                    type=EligibilityCheckType.NFT_COLLECTION,
                    category=rule.category,
                    asset=NftCollectionAsset.from_string(rule.asset),
                    expected=rule.threshold,
                    title=(
                        rule.asset
                        or (rule.nft_collection.name if rule.nft_collection else None)
                    ),
                    address_raw=rule.address,
                    actual=(
                        len(
                            find_relevant_nft_items(rule=rule, nft_items=user_nft_items)
                        )
                    ),
                    is_enabled=rule.is_enabled,
                    collection=NftCollectionDTO.from_orm(rule.nft_collection),
                )
                for rule in eligibility_rules.nft_collections
            ]
        )
        items.extend(
            [
                EligibilitySummaryInternalDTO(
                    id=rule.id,
                    group_id=rule.group_id,
                    type=EligibilityCheckType.PREMIUM,
                    expected=1,
                    title="Telegram Premium",
                    actual=user.is_premium,
                    is_enabled=rule.is_enabled,
                )
                for rule in eligibility_rules.premium
            ]
        )
        items.extend(
            [
                EligibilitySummaryStickerCollectionInternalDTO(
                    id=rule.id,
                    group_id=rule.group_id,
                    type=EligibilityCheckType.STICKER_COLLECTION,
                    expected=rule.threshold,
                    title=(
                        rule.category
                        or (rule.character.name if rule.character else None)
                        or (rule.collection.title if rule.collection else None)
                    ),
                    collection=MinimalStickerCollectionDTO.from_orm(rule.collection)
                    if rule.collection
                    else None,
                    character=MinimalStickerCharacterDTO.from_orm(rule.character)
                    if rule.character
                    else None,
                    actual=len(
                        find_relevant_sticker_items(
                            rule=rule, sticker_items=user_sticker_items
                        )
                    ),
                    is_enabled=rule.is_enabled,
                )
                for rule in eligibility_rules.stickers
            ]
        )
        items.extend(
            [
                EligibilitySummaryGiftCollectionInternalDTO(
                    id=rule.id,
                    group_id=rule.group_id,
                    type=EligibilityCheckType.GIFT_COLLECTION,
                    expected=rule.threshold,
                    title=(rule.collection.title if rule.collection else rule.category),
                    category=rule.category,
                    collection=GiftCollectionDTO.from_orm(rule.collection)
                    if rule.collection
                    else None,
                    model=rule.model,
                    backdrop=rule.backdrop,
                    pattern=rule.pattern,
                    actual=len(
                        find_relevant_gift_items(rule=rule, gift_items=user_gift_items)
                    ),
                    is_enabled=rule.is_enabled,
                )
                for rule in eligibility_rules.gifts
            ]
        )
        items.extend(
            [
                EligibilitySummaryInternalDTO(
                    id=rule.id,
                    group_id=rule.group_id,
                    type=EligibilityCheckType.EMOJI,
                    expected=1,
                    title=rule.emoji_id,
                    actual=1,
                    is_enabled=rule.is_enabled,
                )
                for rule in eligibility_rules.emoji
            ]
        )
        items.extend(
            [
                EligibilitySummaryInternalDTO(
                    id=rule.id,
                    group_id=rule.group_id,
                    type=EligibilityCheckType.WHITELIST,
                    expected=1,
                    title=rule.name,
                    actual=cls.is_whitelisted(user=user, rule=rule),
                    is_enabled=rule.is_enabled,
                )
                for rule in eligibility_rules.whitelist_sources
            ]
        )
        items.extend(
            [
                EligibilitySummaryInternalDTO(
                    id=rule.id,
                    group_id=rule.group_id,
                    type=EligibilityCheckType.EXTERNAL_SOURCE,
                    expected=1,
                    title=rule.name,
                    actual=cls.is_whitelisted(user=user, rule=rule),
                    is_enabled=rule.is_enabled,
                )
                for rule in eligibility_rules.whitelist_external_sources
            ]
        )
        # Group items by group ID
        groups = defaultdict(list)
        for item in items:
            groups[item.group_id].append(item)

        return RulesEligibilitySummaryInternalDTO(
            groups=[
                RulesEligibilityGroupSummaryInternalDTO(
                    items=group_items,
                    id=group_id,
                )
                for group_id, group_items in groups.items()
            ],
            wallet=user_wallet.address if user_wallet else None,
        )

    @staticmethod
    def is_whitelisted(
        user: User, rule: TelegramChatWhitelist | TelegramChatWhitelistExternalSource
    ) -> bool:
        """
        Check if user is in whitelist by the rule
        :param user: User to check
        :param rule: Whitelist rule to check
        :return: True if user is whitelisted
        """
        return user.telegram_id in rule.content

    async def kick_chat_member(self, chat_member: TelegramChatUser) -> None:
        if not chat_member.is_managed:
            logger.warning(
                f"Attempt to kick non-managed chat member {chat_member.chat_id=} and {chat_member.user_id=}. Skipping."
            )
            return

        if chat_member.chat.insufficient_privileges:
            logger.warning(
                f"Attempt to kick chat member {chat_member.chat_id=} and {chat_member.user_id=} "
                f"failed as bot was lacking privileges to manage the chat. Skipping."
            )
            return

        await self.telethon_service.start()
        try:
            await self.telethon_service.kick_chat_member(
                chat_id=chat_member.chat_id,
                telegram_user_id=chat_member.user.telegram_id,
            )
            if chat_member.user.allows_write_to_pm:
                await self.telethon_service.send_message(
                    chat_id=chat_member.user.telegram_id,
                    message=f"You were kicked out of the **{chat_member.chat.title}**.",
                )
            self.telegram_chat_user_service.delete(
                chat_id=chat_member.chat_id, user_id=chat_member.user.id
            )
            logger.info(
                f"User {chat_member.user.telegram_id!r} was kicked from chat {chat_member.chat_id!r}"
            )
        except UserAdminInvalidError as e:
            logger.warning(
                f"Failed to kick user {chat_member.user.telegram_id!r} from chat {chat_member.chat_id!r} as bot user lacks admin privileges",
                exc_info=e,
            )
            telegram_chat_service = TelegramChatService(self.db_session)
            telegram_chat_service.set_insufficient_privileges(
                chat_id=chat_member.chat_id, value=True
            )
            logger.info(
                f"Set insufficient privileges flag for chat {chat_member.chat_id!r}."
            )
        except RPCError as e:
            logger.error(
                f"Failed to kick user {chat_member.user.telegram_id!r} from chat {chat_member.chat_id!r}",
                exc_info=e,
            )

    async def kick_ineligible_chat_members(
        self,
        chat_members: list[TelegramChatUser],
    ) -> None:
        ineligible_members = self.get_ineligible_chat_members(chat_members=chat_members)
        if not ineligible_members:
            logger.info("No ineligible chat members found")
            return

        logger.info(f"Found {len(ineligible_members)} ineligible chat members")

        for member in ineligible_members:
            try:
                await self.kick_chat_member(member)
            except MissingChatEntityError as e:
                logger.error(
                    f"Failed to kick chat member {member.chat_id=} and {member.user_id=} as chat entity is missing",
                    exc_info=e,
                )
            except MissingUserEntityError as e:
                logger.error(
                    f"Failed to kick chat member {member.chat_id=} and {member.user_id=} as user entity is missing",
                    exc_info=e,
                )
