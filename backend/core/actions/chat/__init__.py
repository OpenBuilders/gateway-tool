import logging
from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from starlette.status import HTTP_502_BAD_GATEWAY, HTTP_409_CONFLICT
from telethon import TelegramClient
from telethon.errors import ChatAdminRequiredError, RPCError

from core.actions.authorization import AuthorizationAction
from core.actions.base import BaseAction
from core.actions.chat.base import ManagedChatBaseAction
from core.dtos.chat import (
    TelegramChatDTO,
    TelegramChatPovDTO,
)
from core.dtos.chat.rule import (
    TelegramChatWithRulesDTO,
    EligibilityCheckType,
    ChatEligibilityRuleDTO,
    ChatEligibilityRuleGroupDTO,
)
from core.dtos.chat.rule.emoji import (
    EmojiChatEligibilitySummaryDTO,
    EmojiChatEligibilityRuleDTO,
)
from core.dtos.chat.rule.gift import (
    GiftChatEligibilityRuleDTO,
    GiftChatEligibilitySummaryDTO,
)
from core.dtos.chat.rule.jetton import (
    JettonEligibilityRuleDTO,
    JettonEligibilitySummaryDTO,
)
from core.dtos.chat.rule.nft import NftEligibilityRuleDTO, NftRuleEligibilitySummaryDTO
from core.dtos.chat.rule.sticker import (
    StickerChatEligibilityRuleDTO,
    StickerChatEligibilitySummaryDTO,
)
from core.dtos.chat.rule.summary import (
    RuleEligibilitySummaryDTO,
    TelegramChatWithEligibilitySummaryDTO,
    TelegramChatGroupWithEligibilitySummaryDTO,
)
from core.exceptions.chat import (
    TelegramChatNotExists,
)
from core.models.chat import TelegramChat
from core.models.user import User
from core.services.cdn import CDNService
from core.services.chat import TelegramChatService
from core.services.chat.rule.group import TelegramChatRuleGroupService
from core.services.chat.user import TelegramChatUserService
from core.services.supertelethon import TelethonService
from core.settings import core_settings

logger = logging.getLogger(__name__)


class TelegramChatAction(BaseAction):
    def __init__(
        self, db_session: Session, telethon_client: TelegramClient | None = None
    ):
        super().__init__(db_session)
        self.telegram_chat_service = TelegramChatService(db_session)
        self.telegram_chat_user_service = TelegramChatUserService(db_session)
        self.telegram_chat_rule_group_service = TelegramChatRuleGroupService(db_session)
        self.authorization_action = AuthorizationAction(
            db_session, telethon_client=telethon_client
        )
        self.telethon_service = TelethonService(
            client=telethon_client, bot_token=core_settings.telegram_bot_token
        )
        self.cdn_service = CDNService()

    def get_all(self, requestor: User) -> list[TelegramChatDTO]:
        """
        Retrieves all Telegram chats managed by the given user.

        This method fetches all chats that the specified user has the authority to
        manage and converts them into DTOs (Data Transfer Objects).

        :param requestor: The user requesting the list of managed Telegram chats.
        :return: A list of DTOs, each representing a managed Telegram chat.
        """
        chats = self.telegram_chat_service.get_all_managed(user_id=requestor.id)

        members_count = self.telegram_chat_user_service.get_members_count_by_chat_id(
            [chat.id for chat in chats]
        )

        return [
            TelegramChatDTO.from_object(chat, members_count=members_count[chat.id])
            for chat in chats
        ]

    async def get_with_eligibility_summary(
        self, slug: str, user: User
    ) -> TelegramChatWithEligibilitySummaryDTO:
        """
        Retrieve a chat's details with the user's eligibility summary.
        This is a **non-administrative** user action.

        This method fetches the specified Telegram chat details and determines the
        user's eligibility to access the chat. It also processes eligibility rules and
        provides a summary based on the supplied user and chat information. The chat
        data, eligibility rules, and membership details are encapsulated and returned
        in the response DTO.

        :param slug: The unique slug identifier for the Telegram chat.
        :param user: The user for whom the eligibility summary is to be generated.
        :return: A data transfer object containing the Telegram chat details and the
            eligibility summary for the user.
        :raises TelegramChatNotExists: If the Telegram chat with the specified slug
            does not exist.
        """
        try:
            chat = self.telegram_chat_service.get_by_slug(slug)
        except NoResultFound:
            logger.warning(f"Chat with slug {slug!r} not found")
            raise TelegramChatNotExists(f"Chat with slug {slug!r} not found")

        if not chat.is_enabled:
            # Don't pull any records from the DB and just hide the chat page
            return TelegramChatWithEligibilitySummaryDTO(
                chat=TelegramChatPovDTO.from_object(
                    chat,
                    is_member=False,
                    is_eligible=False,
                    join_url=None,
                    members_count=0,
                ),
                rules=[],
                groups=[],
                wallet=None,
            )

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
            EligibilityCheckType.JETTON: JettonEligibilitySummaryDTO,
            EligibilityCheckType.NFT_COLLECTION: NftRuleEligibilitySummaryDTO,
            EligibilityCheckType.EMOJI: EmojiChatEligibilitySummaryDTO,
            EligibilityCheckType.STICKER_COLLECTION: StickerChatEligibilitySummaryDTO,
            EligibilityCheckType.GIFT_COLLECTION: GiftChatEligibilitySummaryDTO,
        }

        members_count = self.telegram_chat_user_service.get_members_count(chat.id)

        formatted_groups = [
            TelegramChatGroupWithEligibilitySummaryDTO(
                id=group.id,
                items=[
                    mapping.get(rule.type, RuleEligibilitySummaryDTO).from_internal_dto(
                        rule
                    )
                    for rule in group.items
                ],
            )
            for group in eligibility_summary.groups
        ]

        return TelegramChatWithEligibilitySummaryDTO(
            chat=TelegramChatPovDTO.from_object(
                chat,
                join_url=chat.invite_link if is_eligible else None,
                is_member=is_chat_member,
                is_eligible=is_eligible,
                members_count=members_count,
            ),
            groups=formatted_groups,
            rules=[item for group in formatted_groups for item in group.items],
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

    async def update(self, description: str | None) -> TelegramChatDTO:
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

        members_count = self.telegram_chat_user_service.get_members_count(chat.id)
        return TelegramChatDTO.from_object(chat, members_count=members_count)

    async def get_with_eligibility_rules(self) -> TelegramChatWithRulesDTO:
        """
        This is an administrative method to get chat with rules that includes disabled rules
        :return: DTO with chat and rules
        """
        eligibility_rules = self.authorization_action.get_eligibility_rules(
            chat_id=self.chat.id,
            enabled_only=False,
        )
        members_count = self.telegram_chat_user_service.get_members_count(self.chat.id)

        rules = sorted(
            [
                *(
                    ChatEligibilityRuleDTO.from_toncoin_rule(rule)
                    for rule in eligibility_rules.toncoin
                ),
                *(
                    JettonEligibilityRuleDTO.from_jetton_rule(rule)
                    for rule in eligibility_rules.jettons
                ),
                *(
                    NftEligibilityRuleDTO.from_nft_collection_rule(rule)
                    for rule in eligibility_rules.nft_collections
                ),
                *(
                    ChatEligibilityRuleDTO.from_whitelist_rule(rule)
                    for rule in eligibility_rules.whitelist_sources
                ),
                *(
                    ChatEligibilityRuleDTO.from_whitelist_external_rule(rule)
                    for rule in eligibility_rules.whitelist_external_sources
                ),
                *(
                    ChatEligibilityRuleDTO.from_premium_rule(rule)
                    for rule in eligibility_rules.premium
                ),
                *(
                    StickerChatEligibilityRuleDTO.from_orm(rule)
                    for rule in eligibility_rules.stickers
                ),
                *(
                    GiftChatEligibilityRuleDTO.from_orm(rule)
                    for rule in eligibility_rules.gifts
                ),
                *(
                    EmojiChatEligibilityRuleDTO.from_orm(rule)
                    for rule in eligibility_rules.emoji
                ),
            ],
            key=lambda rule: (not rule.is_enabled, rule.type.value, rule.title),
        )
        groups = self.telegram_chat_rule_group_service.get_all(self.chat.id)
        items = defaultdict(list)
        for rule in rules:
            items[rule.group_id].append(rule)

        return TelegramChatWithRulesDTO(
            chat=TelegramChatDTO.from_object(
                obj=self.chat,
                members_count=members_count,
            ),
            groups=[
                ChatEligibilityRuleGroupDTO(
                    id=group.id,
                    items=items.get(group.id, []),
                )
                # Iterate over original groups to preserve groups ordering
                for group in groups
            ],
            rules=rules,
        )

    async def enable(self) -> TelegramChat:
        """
        Enables the Telegram chat by updating its invite link and marking it as enabled, or skips the operation
        if the chat is already enabled.

        Summary:
        This asynchronous method attempts to enable a Telegram chat by initiating the Telethon
        service, retrieving a new invite link, and updating the associated data for the chat.
        In case of insufficient privileges, an appropriate exception is raised. The method
        either updates the chat state or skips if it is already enabled, ensuring proper
        logging of these operations.

        :return: The updated Telegram chat object with the refreshed invite link and enabled state.

        :raises TelegramChatNotSufficientPrivileges: If the current configuration does not have
            sufficient privileges to perform the operation.
        """
        if self.chat.is_enabled:
            logger.debug(
                f"Chat {self.chat.id!r} is already enabled. Skipping enable operation..."
            )
            return self.chat

        await self.telethon_service.start()
        try:
            peer = await self.telethon_service.get_chat(entity=self.chat.id)
            invite_link = await self.telethon_service.get_invite_link(chat=peer)
            await self.telethon_service.stop()
            chat = self.telegram_chat_service.refresh_invite_link(
                chat_id=self.chat.id, invite_link=invite_link.link
            )
            logger.info(
                f"Updated invite link of chat {chat.id!r} to {invite_link.link!r} and enabled it."
            )
        except ChatAdminRequiredError:
            await self.telethon_service.stop()
            logger.warning(f"Insufficient privileges to enable chat {self.chat.id!r}")
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail=f"Insufficient privileges to enable chat {self.chat.id!r}",
            )
        except RPCError:
            logger.exception(f"Failed to enable chat {self.chat.id!r}")
            raise HTTPException(
                status_code=HTTP_502_BAD_GATEWAY,
                detail=f"Failed to enable chat {self.chat.id!r}",
            )

        return chat

    async def disable(self) -> TelegramChat:
        """
        Disables a Telegram chat by removing its invite link and updating its state.

        This method performs the following operations asynchronously:
        1. Starts the Telethon service.
        2. Removes the invite link associated with the specified chat.
        3. Stops the Telethon service after operations.
        4. Disables the chat using the Telegram chat service.

        If an error occurs due to insufficient admin privileges, a custom exception
        is raised. For any RPC-related failure, an HTTP exception is raised with
        appropriate details.

        :raises HTTPException: If an RPC-related error occurs while disabling the chat.
        :return: The updated chat object with its state disabled.
        """
        await self.telethon_service.start()
        try:
            await self.telethon_service.revoke_chat_invite(
                chat_id=self.chat.id, link=self.chat.invite_link
            )
            await self.telethon_service.stop()
            chat = self.telegram_chat_service.disable(self.chat)
            logger.info(f"Removed invite link of chat {chat.id!r} and disabled it.")
        except ChatAdminRequiredError:
            await self.telethon_service.stop()
            logger.warning(f"Insufficient privileges to disable chat {self.chat.id!r}")
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail=f"Insufficient privileges to disable chat {self.chat.id!r}",
            )
        except RPCError:
            logger.exception(f"Failed to disable chat {self.chat.id!r}")
            raise HTTPException(
                status_code=HTTP_502_BAD_GATEWAY,
                detail=f"Failed to disable chat {self.chat.id!r}",
            )

        return chat

    async def update_visibility(self, is_enabled: bool) -> TelegramChatDTO:
        if is_enabled:
            chat = await self.enable()
        else:
            chat = await self.disable()
        members_count = self.telegram_chat_user_service.get_members_count(chat.id)
        return TelegramChatDTO.from_object(
            obj=chat,
            members_count=members_count,
        )

    async def delete(self) -> None:
        self.telegram_chat_service.delete(self.chat.id)
