import logging

from fastapi import HTTPException
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from core.actions.chat.base import ManagedChatBaseAction
from core.actions.jetton import JettonAction
from core.actions.nft_collection import NftCollectionAction
from core.dtos.chat.rule import ChatEligibilityRuleDTO
from core.dtos.chat.rule.nft import (
    CreateTelegramChatNFTCollectionRuleDTO,
    NftEligibilityRuleDTO,
    UpdateTelegramChatNFTCollectionRuleDTO,
)
from core.dtos.chat.rule.jetton import (
    CreateTelegramChatJettonRuleDTO,
    UpdateTelegramChatJettonRuleDTO,
    JettonEligibilityRuleDTO,
)
from core.dtos.chat.rule.toncoin import (
    CreateTelegramChatToncoinRuleDTO,
    UpdateTelegramChatToncoinRuleDTO,
)
from core.enums.jetton import CurrencyCategory
from core.enums.nft import NftCollectionAsset, NftCollectionCategoryType
from core.exceptions.external import ExternalResourceNotFound
from core.utils.custom_rules.addresses import (
    NFT_ASSET_TO_ADDRESS_MAPPING,
    NFT_CATEGORY_TO_ADDRESS_MAPPING,
)
from core.models.user import User
from core.services.chat.rule.blockchain import (
    TelegramChatNFTCollectionService,
    TelegramChatJettonService,
    TelegramChatToncoinService,
)

logger = logging.getLogger(__name__)


class TelegramChatNFTCollectionAction(ManagedChatBaseAction):
    def __init__(self, db_session: Session, requestor: User, chat_slug: str) -> None:
        super().__init__(
            db_session=db_session, requestor=requestor, chat_slug=chat_slug
        )
        self.telegram_chat_nft_collection_service = TelegramChatNFTCollectionService(
            db_session
        )
        self.nft_collection_action = NftCollectionAction(db_session)

    def read(self, rule_id: int) -> NftEligibilityRuleDTO:
        try:
            rule = self.telegram_chat_nft_collection_service.get(
                rule_id, chat_id=self.chat.id
            )
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )
        return NftEligibilityRuleDTO.from_nft_collection_rule(rule)

    @staticmethod
    def _resolve_collection_address(
        address_raw: str,
        asset: NftCollectionAsset | None,
        category: NftCollectionCategoryType | None,
    ) -> str | None:
        """
        Resolves the collection address based on the provided parameters. The resolution
        is determined in the following order of priority:
        1. If the `category` is provided, it attempts to resolve the address using the
           `NFT_CATEGORY_TO_ADDRESS_MAPPING`.
        2. If the `asset` is provided, it attempts to resolve the address using the
           `NFT_ASSET_TO_ADDRESS_MAPPING`.
        3. If `address_raw` is provided, it will use the raw address directly.

        If none of the above options yields an address, `None` will be returned.

        :param address_raw: The raw address string explicitly provided.
        :param asset: The asset type for the NFT collection, used to map to a specific
            address.
        :param category: The category type for the NFT collection, used to map to a
            specific address.
        :return: The resolved collection address or None if no valid resolution is found.
        """
        if category:
            # If there is a mapping by category, that is the lowest level - return that address
            if address := NFT_CATEGORY_TO_ADDRESS_MAPPING.get(category):
                return address

        if asset:
            # If there is a mapping by asset type - return that address
            if address := NFT_ASSET_TO_ADDRESS_MAPPING.get(asset):
                return address

        elif address_raw:
            # If no asset selected and explicit address provided - use that address
            return address_raw

        return None

    def check_duplicate(
        self,
        chat_id: int,
        group_id: int,
        address_raw: str | None,
        asset: NftCollectionAsset | None,
        category: NftCollectionCategoryType | None,
        entity_id: int | None = None,
    ) -> None:
        """
        Checks for duplicate rules in the Telegram chat collection service. This function ensures
        that no duplicate rules of the same type and category exist for a specific chat. If such
        a rule exists, an exception is raised instructing the user to modify the existing rule
        instead of creating a new one.

        This method performs the check by retrieving existing rules based on the provided chat ID,
        address, asset, and category, filtering out rules with the same ID as the supplied entity ID
        (if provided), and checking for duplicates.

        :param chat_id: The unique identifier for the Telegram chat where the rule applies.
        :param group_id: The unique identifier for the group where the rule applies.
        :param address_raw: The address associated with the rule (optional).
        :param asset: The asset associated with the rule, of type NftCollectionAsset (optional).
        :param category: The category of the currency to which the rule applies, defined
            as NftCollectionCategoryType (optional).
        :param entity_id: The unique identifier for an existing rule to exclude from duplicate
            checks (optional).
        :return: None. The function raises an exception if a duplicate rule exists.
        :raises HTTPException: Raised if a rule of the same type and category already exists
            for the specified chat, excluding the rule with the provided `entity_id`.
        """
        existing_rules = self.telegram_chat_nft_collection_service.find(
            chat_id=chat_id,
            group_id=group_id,
            address=address_raw,
            asset=asset,
            category=category,
        )
        if next(filter(lambda rule: rule.id != entity_id, existing_rules), None):
            raise HTTPException(
                detail="Rule of that type and category already exists for that chat. Please, modify it instead.",
                status_code=HTTP_400_BAD_REQUEST,
            )

    async def create(
        self,
        group_id: int | None,
        asset: NftCollectionAsset | None,
        address_raw: str | None,
        category: NftCollectionCategoryType | None,
        threshold: int,
    ) -> NftEligibilityRuleDTO:
        """
        Creates a new NFT eligibility rule by linking a chat to an NFT collection. It resolves
        the NFT collection's address based on the provided parameters and ensures that there
        are no duplicate rules for the same chat and collection.

        :param asset: Represents an optional NFT collection asset. This asset is used to
            resolve the NFT collection address.
        :param address_raw: The raw address of the NFT collection. This may be used in resolving
            the final collection address.
        :param category: Represents an optional category of the NFT collection.
        :param threshold: An integer value specifying the threshold condition for the rule.
        :param group_id: An optional integer value specifying the group ID for the rule.

        :return: A data transfer object (DTO) representing the created NFT eligibility rule.
            The DTO encapsulates all properties of the rule created for the chat and
            NFT collection.
        """
        address = self._resolve_collection_address(address_raw, asset, category)
        group_id = self.resolve_group_id(group_id=group_id)

        if not address:
            logger.error(
                f"Can't resolve address of the NFT collection for the provided details: {asset=}, {address_raw=}, {category=}"
            )
            raise HTTPException(
                detail="Can't resolve address of the NFT collection",
                status_code=HTTP_400_BAD_REQUEST,
            )

        nft_collection_dto = await self.nft_collection_action.get_or_create(address)
        self.check_duplicate(
            chat_id=self.chat.id,
            group_id=group_id,
            address_raw=nft_collection_dto.address,
            asset=asset,
            category=category,
        )

        new_rule = self.telegram_chat_nft_collection_service.create(
            CreateTelegramChatNFTCollectionRuleDTO(
                group_id=group_id,
                category=category,
                asset=asset,
                chat_id=self.chat.id,
                address=address,
                threshold=threshold,
                is_enabled=True,
            )
        )
        logger.info(
            f"Chat {self.chat.id!r} linked to NFT collection {address!r} and asset {asset!r}"
        )
        return NftEligibilityRuleDTO.from_nft_collection_rule(new_rule)

    async def update(
        self,
        rule_id: int,
        asset: NftCollectionAsset | None,
        address_raw: str | None,
        category: NftCollectionCategoryType | None,
        threshold: int,
        is_enabled: bool,
    ) -> NftEligibilityRuleDTO:
        """
        Updates an existing NFT eligibility rule for a specific chat.

        This method retrieves the rule by ID and updates it with the provided
        details. It ensures the NFT collection address is resolved based on
        the provided asset and category, creates or retrieves the corresponding
        NFT collection if necessary, and checks for duplicate rules. The updated
        rule is then returned as a data transfer object (DTO).

        :param rule_id: The unique identifier of the rule to be updated.
        :param asset: The NFT collection asset associated with the rule,
            or None if not provided.
        :param address_raw: The raw address of the NFT collection, or None.
        :param category: The NFT collection category type associated with the
            rule, or None if not provided.
        :param threshold: The minimum threshold value for rule activation.
        :param is_enabled: A boolean flag indicating whether the rule is
            currently enabled.
        :return: A data transfer object (DTO) representing the updated
            NFT eligibility rule.
        :raises HTTPException: If the rule with the provided ID does not exist,
            there is a problem resolving the NFT collection address or
            rule duplication is detected.
        """
        try:
            rule = self.telegram_chat_nft_collection_service.get(
                rule_id, chat_id=self.chat.id
            )
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )

        address = self._resolve_collection_address(address_raw, asset, category)

        if not address:
            logger.error(
                f"Can't resolve address of the NFT collection for the provided details: {asset=}, {address_raw=}, {category=}"
            )
            raise HTTPException(
                detail="Can't resolve address of the NFT collection",
                status_code=HTTP_400_BAD_REQUEST,
            )

        nft_collection_dto = await self.nft_collection_action.get_or_create(address)
        self.check_duplicate(
            chat_id=self.chat.id,
            group_id=rule.group_id,
            address_raw=nft_collection_dto.address,
            asset=asset,
            category=category,
            entity_id=rule.id,
        )

        rule = self.telegram_chat_nft_collection_service.update(
            rule=rule,
            dto=UpdateTelegramChatNFTCollectionRuleDTO(
                asset=asset,
                address=address,
                category=category,
                threshold=threshold,
                is_enabled=is_enabled,
            ),
        )
        logger.info(
            f"Updated chat nft collection rule {rule_id!r} with address {address!r} and asset {asset!r}"
        )
        return NftEligibilityRuleDTO.from_nft_collection_rule(rule)

    async def delete(self, rule_id: int) -> None:
        try:
            group_id = self.telegram_chat_nft_collection_service.get(
                rule_id, chat_id=self.chat.id
            ).group_id
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )
        self.telegram_chat_nft_collection_service.delete(rule_id, chat_id=self.chat.id)
        logger.info(f"Deleted chat nft collection rule {rule_id!r}")
        self.remove_group_if_empty(group_id=group_id)


class TelegramChatJettonAction(ManagedChatBaseAction):
    def __init__(self, db_session: Session, requestor: User, chat_slug: str) -> None:
        super().__init__(
            db_session=db_session, requestor=requestor, chat_slug=chat_slug
        )
        self.telegram_chat_jetton_service = TelegramChatJettonService(db_session)
        self.jetton_action = JettonAction(db_session)

    def read(self, rule_id: int) -> JettonEligibilityRuleDTO:
        try:
            rule = self.telegram_chat_jetton_service.get(rule_id, chat_id=self.chat.id)
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )
        return JettonEligibilityRuleDTO.from_jetton_rule(rule)

    def check_duplicate(
        self,
        chat_id: int,
        group_id: int,
        address_raw: str,
        category: CurrencyCategory | None,
        entity_id: int | None = None,
    ) -> None:
        """
        Checks for duplicate rules in the system based on provided criteria.

        This method verifies whether a duplicate rule exists for the given chat ID,
        address, and category, excluding the rule specified by the entity ID. If a
        duplicate is found, it raises an HTTPException indicating the conflict.

        This is typically used to enforce uniqueness constraints and ensure that no
        redundant rules are added to the system.

        :param chat_id: ID of the Telegram chat for which the rule is being verified
        :param group_id: ID of the group for which the rule is being verified
        :param address_raw: Address of the entity to be checked for duplicate rules
        :param category: Category of the currency to filter the rules
        :param entity_id: Identifier of the existing rule to exclude from duplicate
            checks; this can be None if no existing rule is to be excluded
        :return: None. The function raises an error if a duplicate rule is found.
        """
        existing_rules = self.telegram_chat_jetton_service.find(
            chat_id=chat_id,
            group_id=group_id,
            address=address_raw,
            category=category,
        )
        if next(filter(lambda rule: rule.id != entity_id, existing_rules), None):
            raise HTTPException(
                detail="Rule of that type and category already exists for that chat. Please, modify it instead.",
                status_code=HTTP_400_BAD_REQUEST,
            )

    async def create(
        self,
        group_id: int | None,
        address_raw: str,
        category: CurrencyCategory | None,
        threshold: float | int,
    ) -> JettonEligibilityRuleDTO:
        """
        Creates and associates a new chat-eligibility rule for a specific jetton, with
        options to set a category and a threshold. Ensures duplication prevention
        before rule creation. Logs the operation's activity and returns the created
        rule mapped to a DTO.

        :param address_raw: The raw address of the jetton to associate.
        :param category: The category of the currency or jetton, if applicable.
        :param threshold: The minimum threshold value to set for the rule.
        :param group_id: The group ID to associate with the rule, if applicable.
        :return: A data transfer object (DTO) representing the created chat-eligibility
            rule linked to the jetton.
        :raises HTTPException: If there is a problem resolving the jetton address or
            the rule duplication is detected.
        """
        try:
            jetton_dto = await self.jetton_action.get_or_create(address_raw)
        except ExternalResourceNotFound:
            raise HTTPException(
                detail="Can't resolve jetton address",
                status_code=HTTP_400_BAD_REQUEST,
            )

        group_id = self.resolve_group_id(group_id=group_id)

        self.check_duplicate(
            chat_id=self.chat.id,
            group_id=group_id,
            address_raw=jetton_dto.address,
            category=category,
        )

        new_rule = self.telegram_chat_jetton_service.create(
            CreateTelegramChatJettonRuleDTO(
                chat_id=self.chat.id,
                group_id=group_id,
                address=jetton_dto.address,
                category=category,
                threshold=threshold,
                is_enabled=True,
            )
        )
        logger.info(f"Chat {self.chat.id!r} linked to jetton {jetton_dto.address!r}")
        return JettonEligibilityRuleDTO.from_jetton_rule(new_rule)

    async def update(
        self,
        rule_id: int,
        address_raw: str,
        category: CurrencyCategory | None,
        threshold: int | float,
        is_enabled: bool,
    ) -> JettonEligibilityRuleDTO:
        """
        Updates an existing chat jetton rule with specified parameters.

        This method fetches the existing rule using the provided `rule_id` and updates it with
        new values supplied as arguments. It also ensures no duplicate rules exist with the
        same parameters. If the rule does not exist, an HTTPException with status code 404 is
        raised. The updated rule information is wrapped into a `ChatEligibilityRuleDTO` and
        returned.

        :param rule_id: Identifier of the rule to be updated
        :param address_raw: Raw address to be associated with the rule
        :param category: Category of the currency, could be optional
        :param threshold: Threshold value for the rule, could be an integer or float
        :param is_enabled: Boolean flag indicating if the rule is enabled
        :return: A `ChatEligibilityRuleDTO` object representing the updated rule
        :raises HTTPException: If the rule with the provided `rule_id` does not exist,
            if there is a problem resolving the jetton address or rule duplication is detected.
        """
        try:
            rule = self.telegram_chat_jetton_service.get(rule_id, chat_id=self.chat.id)
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )
        jetton_dto = await self.jetton_action.get_or_create(address_raw)

        self.check_duplicate(
            chat_id=self.chat.id,
            group_id=rule.group_id,
            address_raw=jetton_dto.address,
            category=category,
            entity_id=rule.id,
        )

        updated_rule = self.telegram_chat_jetton_service.update(
            rule=rule,
            dto=UpdateTelegramChatJettonRuleDTO(
                address=jetton_dto.address,
                category=category,
                threshold=threshold,
                is_enabled=is_enabled,
            ),
        )
        logger.info(
            f"Updated chat jetton rule {rule_id!r} with address {jetton_dto.address!r}"
        )
        return JettonEligibilityRuleDTO.from_jetton_rule(updated_rule)

    async def delete(self, rule_id: int) -> None:
        try:
            group_id = self.telegram_chat_jetton_service.get(
                rule_id, chat_id=self.chat.id
            ).group_id
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )
        self.telegram_chat_jetton_service.delete(rule_id, chat_id=self.chat.id)
        logger.info(f"Deleted chat jetton rule {rule_id!r}")
        self.remove_group_if_empty(group_id=group_id)


class TelegramChatToncoinAction(ManagedChatBaseAction):
    def __init__(self, db_session: Session, requestor: User, chat_slug: str) -> None:
        super().__init__(
            db_session=db_session, requestor=requestor, chat_slug=chat_slug
        )
        self.telegram_chat_toncoin_service = TelegramChatToncoinService(db_session)

    def read(self, rule_id: int) -> ChatEligibilityRuleDTO:
        try:
            rule = self.telegram_chat_toncoin_service.get(rule_id, chat_id=self.chat.id)
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )
        return ChatEligibilityRuleDTO.from_toncoin_rule(rule)

    def check_duplicate(
        self,
        chat_id: int,
        group_id: int,
        category: CurrencyCategory | None,
        entity_id: int | None = None,
    ) -> None:
        """
        Checks for existing rules in the service to determine if a duplicate rule exists for the specified
        chat, category, and optionally the entity ID. If a duplicate is found, an HTTPException is raised.

        :param chat_id: The identifier of the chat to check for duplicate rules.
        :param group_id: The identifier of the group to check for duplicate rules.
        :param category: The category of the rule to check for duplication.
        :param entity_id: The unique identifier of the rule entity. It is optional and defaults to None.
        :return: None. It raises an HTTPException if a duplicate rule is found.
        :raises HTTPException: If a duplicate rule of the specified type and category is found.
        """
        existing_rules = self.telegram_chat_toncoin_service.find(
            chat_id=chat_id,
            group_id=group_id,
            category=category,
        )
        if next(filter(lambda rule: rule.id != entity_id, existing_rules), None):
            raise HTTPException(
                detail="Rule of that type and category already exists for that chat. Please, modify it instead.",
                status_code=HTTP_400_BAD_REQUEST,
            )

    def create(
        self,
        group_id: int | None,
        category: CurrencyCategory | None,
        threshold: float | int,
    ) -> ChatEligibilityRuleDTO:
        """
        Creates a new chat eligibility rule based on the specified category and
        threshold.

        This method verifies if there is an existing rule for the specified category
        in the current chat. If no duplicate exists, it creates and associates a
        new TON rule with the chat while enabling the rule by default. The method
        logs the creation event and returns a data transfer object (DTO) that
        represents the newly created TON rule.

        :param category: The currency category to associate with the new TON rule.
        :param threshold: The minimum threshold value for the TON rule.
        :param group_id: The group ID to associate with the new TON rule, if applicable.
        :return: A DTO representing the chat eligibility rule created from the
                 TON rule.
        :raises HTTPException: If a duplicate rule of the specified type and category is found.
        """
        group_id = self.resolve_group_id(group_id=group_id)
        self.check_duplicate(chat_id=self.chat.id, group_id=group_id, category=category)
        new_rule = self.telegram_chat_toncoin_service.create(
            CreateTelegramChatToncoinRuleDTO(
                chat_id=self.chat.id,
                group_id=group_id,
                category=category,
                threshold=threshold,
                is_enabled=True,
            )
        )
        logger.info(f"Chat {self.chat.id!r} linked to a new TON rule")
        return ChatEligibilityRuleDTO.from_toncoin_rule(new_rule)

    def update(
        self,
        rule_id: int,
        category: CurrencyCategory | None,
        threshold: int | float,
        is_enabled: bool,
    ) -> ChatEligibilityRuleDTO:
        """
        Updates an existing chat eligibility rule for TON based on the provided attributes.
        Retrieves the rule by its ID and ensures it belongs to the current chat. Checks for
        duplicate rules before applying updates.

        :param rule_id: The unique identifier of the rule to be updated.
        :param category: The category of the currency for the rule, or None if not applicable.
        :param threshold: The threshold value associated with the rule, could be an integer or float.
        :param is_enabled: A boolean indicating whether the rule is enabled or disabled.
        :return: A data transfer object (DTO) representing the updated chat eligibility rule for TON.
        :raises HTTPException: If the rule with the provided ID does not exist,
            or if a duplicate rule of the specified type and category is found.
        """
        try:
            rule = self.telegram_chat_toncoin_service.get(rule_id, chat_id=self.chat.id)
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )
        self.check_duplicate(
            chat_id=self.chat.id,
            group_id=rule.group_id,
            category=category,
            entity_id=rule.id,
        )

        updated_rule = self.telegram_chat_toncoin_service.update(
            rule=rule,
            dto=UpdateTelegramChatToncoinRuleDTO(
                category=category,
                threshold=threshold,
                is_enabled=is_enabled,
            ),
        )
        logger.info(f"Updated chat jetton rule {rule_id!r} for TON")
        return ChatEligibilityRuleDTO.from_toncoin_rule(updated_rule)

    def delete(self, rule_id: int) -> None:
        try:
            group_id = self.telegram_chat_toncoin_service.get(
                rule_id, chat_id=self.chat.id
            ).group_id
        except NoResultFound:
            raise HTTPException(
                detail="Rule not found",
                status_code=HTTP_404_NOT_FOUND,
            )
        self.telegram_chat_toncoin_service.delete(rule_id, chat_id=self.chat.id)
        logger.info(f"Deleted chat TON rule {rule_id!r}")

        self.remove_group_if_empty(group_id=group_id)
