import logging
import re
from collections.abc import Callable
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    Field,
    AnyHttpUrl,
    model_validator,
    PlainSerializer,
)
from pytonapi.utils import raw_to_userfriendly, userfriendly_to_raw

from api.pos.base import BaseFDO
from api.pos.fields import AmountFacadeField, CDNImageField, AmountInputField
from api.pos.gift import GiftCollectionFDO
from api.pos.sticker import MinimalStickerCharacterFDO, MinimalStickerCollectionFDO
from core.constants import USER_FRIENDLY_ADDRESS_REGEX, RAW_ADDRESS_REGEX
from core.dtos.chat import (
    TelegramChatDTO,
    TelegramChatPovDTO,
)
from core.dtos.chat.rules import (
    EligibilityCheckType,
    ChatEligibilityRuleDTO,
    TelegramChatWithRulesDTO,
)
from core.dtos.chat.rules.emoji import (
    EmojiChatEligibilityRuleDTO,
    EmojiChatEligibilitySummaryDTO,
)
from core.dtos.chat.rules.gift import (
    GiftChatEligibilityRuleDTO,
    GiftChatEligibilitySummaryDTO,
)
from core.dtos.chat.rules.jetton import (
    JettonEligibilityRuleDTO,
    JettonEligibilitySummaryDTO,
)
from core.dtos.chat.rules.sticker import (
    StickerChatEligibilityRuleDTO,
    StickerChatEligibilitySummaryDTO,
)
from core.dtos.chat.rules.summary import (
    RuleEligibilitySummaryDTO,
    TelegramChatWithEligibilitySummaryDTO,
)
from core.dtos.chat.rules.whitelist import (
    WhitelistRuleDTO,
    WhitelistRuleExternalDTO,
    WhitelistRuleCPO,
)
from core.dtos.chat.rules.nft import NftEligibilityRuleDTO, NftRuleEligibilitySummaryDTO
from core.dtos.base import NftItemAttributeDTO
from core.enums.jetton import CurrencyCategory
from core.enums.nft import (
    NftCollectionAsset,
    NftCollectionCategoryType,
    ASSET_TO_CATEGORY_TYPE_MAPPING,
)

logger = logging.getLogger(__name__)

CHAT_INPUT_REGEX = re.compile(
    r"^(?P<chat_id>-?\d+(\.\d+)?)|^(https:\/\/t\.me\/(?P<username>[a-zA-Z0-9_]{4,32}))$"
)


class TelegramChatFDO(BaseFDO, TelegramChatDTO):
    logo_path: CDNImageField


class TelegramChatPovFDO(BaseFDO, TelegramChatPovDTO):
    logo_path: CDNImageField


def validate_chat_identifier(v: str) -> str | int:
    match = CHAT_INPUT_REGEX.match(str(v))
    if not match:
        raise ValueError("Invalid chat input: must be chat ID or username")

    if match.group("username"):
        return match.group("username")

    return int(match.group("chat_id"))


def validate_address(is_required: bool) -> Callable[[str | None], str | None]:
    def _inner(v: str | None) -> str | None:
        if not v:
            if is_required:
                raise ValueError("Missing blockchain address")
            return v

        if USER_FRIENDLY_ADDRESS_REGEX.match(v):
            v = userfriendly_to_raw(v)

        elif RAW_ADDRESS_REGEX.match(v):
            try:
                # To validate the blockchain address
                raw_to_userfriendly(v)
            except ValueError:
                logger.warning(f"Invalid blockchain address: {v!r}")
                raise ValueError("Invalid blockchain address")
            except Exception as e:
                logger.warning(f"Invalid blockchain address: {e}", exc_info=True)
                raise ValueError("Invalid blockchain address")

        return v

    return _inner


class AddChatCPO(BaseFDO):
    chat_identifier: Annotated[str | int, AfterValidator(validate_chat_identifier)]


class EditChatCPO(BaseFDO):
    description: str | None


class ChatVisibilityCPO(BaseFDO):
    is_enabled: bool


class BaseTelegramChatQuantityRuleCPO(BaseFDO):
    expected: Annotated[float | int, Field(..., gt=0, description="Expected value")]
    category: Annotated[
        str | None,
        Field(
            None,
            description="Optional category of the rule, e.g. NFT collection category or amount of burned items",
        ),
    ]
    is_enabled: bool = True


class BaseTelegramChatBlockchainResourceRuleCPO(BaseTelegramChatQuantityRuleCPO):
    address: Annotated[
        str,
        Field(..., description="Raw blockchain address of the item, e.g. 0:..."),
        AfterValidator(validate_address(True)),
    ]


class TelegramChatToncoinRuleCPO(BaseTelegramChatQuantityRuleCPO):
    category: CurrencyCategory = CurrencyCategory.BALANCE
    expected: AmountInputField


class TelegramChatJettonRuleCPO(BaseTelegramChatBlockchainResourceRuleCPO):
    category: CurrencyCategory = CurrencyCategory.BALANCE
    expected: AmountInputField


class NftItemAttributeFDO(BaseFDO, NftItemAttributeDTO):
    ...


class TelegramChatNFTCollectionRuleCPO(BaseTelegramChatBlockchainResourceRuleCPO):
    address: Annotated[
        str | None,
        Field(None, description="Raw blockchain address of the item, e.g. 0:..."),
        AfterValidator(validate_address(is_required=False)),
    ]
    category: NftCollectionCategoryType | None = None
    asset: NftCollectionAsset | None = None

    @model_validator(mode="after")
    def validate_address_and_asset(self) -> Self:
        """
        Validates the mutually exclusive condition of the `address` and `asset` attributes.

        Ensures that either the `address` or the `asset` attribute is specified, but not both.
        Raises a ValueError if the condition is violated.

        :raises ValueError: If both `address` and `asset` are specified or if neither is specified
        """
        if (self.address is None) == (self.asset is None):
            raise ValueError("Either address or asset must be specified, but not both")

        return self

    @model_validator(mode="after")
    def validate_category_and_asset(self) -> Self:
        """
        Validates the combination of category and asset after model creation or updates,
        checking their consistency based on predefined mappings and rules.

        This method ensures that if an asset is specified, an appropriate category
        is either mandatory or optional based on its definition. It also validates
        that the provided category aligns with the corresponding asset, enforcing
        rules defined in the `ASSET_TO_CATEGORY_TYPE_MAPPING`.

        :raises ValueError: If a category is not provided when it's mandatory for the asset,
            or it doesn't match the asset.
        """
        if not self.asset:
            return self

        category_definition = ASSET_TO_CATEGORY_TYPE_MAPPING[self.asset]
        if self.category is None:
            # If a category is mandatory for the asset, it must be provided.
            if not category_definition.is_optional:
                raise ValueError(
                    "Category must be specified if asset is provided for that type of rule"
                )
            return self

        # Otherwise, check if it corresponds a provided asset type
        try:
            self.category = category_definition.enum(self.category.value)
        except ValueError as e:
            raise ValueError("Category does not match asset") from e

        return self


class TelegramChatStickerRuleCPO(BaseTelegramChatQuantityRuleCPO):
    collection_id: int | None
    character_id: int | None

    @model_validator(mode="after")
    def validate_category_or_collection(self) -> Self:
        if not self.category and not self.collection_id:
            raise ValueError("At least category of collection must be specified")

        return self


class TelegramChatGiftRuleCPO(BaseTelegramChatQuantityRuleCPO):
    collection_slug: str | None
    model: str | None
    backdrop: str | None
    pattern: str | None

    @model_validator(mode="after")
    def validate_category_or_collection(self) -> Self:
        if not self.category and not self.collection_slug:
            raise ValueError("At least category of collection must be specified")

        return self


class TelegramChatPremiumRuleCPO(BaseFDO):
    is_enabled: bool


class TelegramChatEmojiRuleCPO(BaseFDO):
    is_enabled: bool
    emoji_id: int


class ChatEligibilityRuleFDO(BaseFDO, ChatEligibilityRuleDTO):
    ...


class ToncoinEligibilityRuleFDO(BaseFDO, ChatEligibilityRuleDTO):
    expected: AmountFacadeField


class JettonEligibilityRuleFDO(BaseFDO, JettonEligibilityRuleDTO):
    photo_url: CDNImageField
    expected: AmountFacadeField
    blockchain_address: Annotated[str, PlainSerializer(raw_to_userfriendly)]


class JettonEligibilitySummaryFDO(BaseFDO, JettonEligibilitySummaryDTO):
    photo_url: CDNImageField
    expected: AmountFacadeField
    actual: AmountFacadeField


class NftEligibilityRuleFDO(BaseFDO, NftEligibilityRuleDTO):
    photo_url: CDNImageField
    blockchain_address: Annotated[str, PlainSerializer(raw_to_userfriendly)]


class NftRuleEligibilitySummaryFDO(BaseFDO, NftRuleEligibilitySummaryDTO):
    photo_url: CDNImageField


class StickerChatEligibilityRuleFDO(BaseFDO, StickerChatEligibilityRuleDTO):
    ...


class StickerChatEligibilitySummaryFDO(BaseFDO, StickerChatEligibilitySummaryDTO):
    collection: MinimalStickerCollectionFDO | None
    character: MinimalStickerCharacterFDO | None


class GiftChatEligibilityRuleFDO(BaseFDO, GiftChatEligibilityRuleDTO):
    photo_url: CDNImageField


class GiftChatEligibilitySummaryFDO(BaseFDO, GiftChatEligibilitySummaryDTO):
    collection: GiftCollectionFDO | None
    photo_url: CDNImageField


class EmojiChatEligibilityRuleFDO(BaseFDO, EmojiChatEligibilityRuleDTO):
    photo_url: CDNImageField


class EmojiChatEligibilitySummaryFDO(BaseFDO, EmojiChatEligibilitySummaryDTO):
    ...


class TelegramChatWithRulesFDO(BaseFDO):
    chat: TelegramChatFDO
    rules: list[
        ChatEligibilityRuleFDO
        | ToncoinEligibilityRuleFDO
        | JettonEligibilityRuleFDO
        | NftEligibilityRuleFDO
        | EmojiChatEligibilityRuleFDO
        | StickerChatEligibilityRuleFDO
        | GiftChatEligibilityRuleFDO
    ]

    @classmethod
    def from_dto(cls, dto: TelegramChatWithRulesDTO) -> Self:
        mapping = {
            EligibilityCheckType.JETTON: JettonEligibilityRuleFDO,
            EligibilityCheckType.TONCOIN: ToncoinEligibilityRuleFDO,
            EligibilityCheckType.NFT_COLLECTION: NftEligibilityRuleFDO,
            EligibilityCheckType.EMOJI: EmojiChatEligibilityRuleFDO,
            EligibilityCheckType.STICKER_COLLECTION: StickerChatEligibilityRuleFDO,
            EligibilityCheckType.GIFT_COLLECTION: GiftChatEligibilityRuleFDO,
        }
        return cls(
            chat=TelegramChatFDO.model_validate(dto.chat.model_dump()),
            rules=[
                mapping.get(rule.type, ChatEligibilityRuleFDO).model_validate(
                    rule.model_dump()
                )
                for rule in dto.rules
            ],
        )


class RuleEligibilitySummaryFDO(BaseFDO, RuleEligibilitySummaryDTO):
    expected: AmountFacadeField
    actual: AmountFacadeField


class TelegramChatWithEligibilitySummaryFDO(BaseFDO):
    """
    Chat with eligibility rules. Returns not only chat and rules data,
    but whether user is eligible for chat
    """

    chat: TelegramChatPovFDO
    rules: list[
        RuleEligibilitySummaryFDO
        | JettonEligibilitySummaryFDO
        | NftRuleEligibilitySummaryFDO
        | EmojiChatEligibilitySummaryFDO
        | StickerChatEligibilitySummaryFDO
        | GiftChatEligibilitySummaryFDO
    ]
    wallet: str | None

    @classmethod
    def from_dto(cls, dto: TelegramChatWithEligibilitySummaryDTO) -> Self:
        mapping = {
            EligibilityCheckType.JETTON: JettonEligibilitySummaryFDO,
            EligibilityCheckType.NFT_COLLECTION: NftRuleEligibilitySummaryFDO,
            EligibilityCheckType.EMOJI: EmojiChatEligibilitySummaryFDO,
            EligibilityCheckType.STICKER_COLLECTION: StickerChatEligibilitySummaryFDO,
            EligibilityCheckType.GIFT_COLLECTION: GiftChatEligibilitySummaryFDO,
        }
        return cls(
            chat=TelegramChatPovFDO.model_validate(dto.chat.model_dump()),
            rules=[
                mapping.get(rule.type, RuleEligibilitySummaryFDO).model_validate(
                    rule.model_dump()
                )
                for rule in dto.rules
            ],
            wallet=dto.wallet,
        )


class CreateWhitelistRuleBaseCPO(BaseFDO):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    description: Annotated[str | None, Field(min_length=0, max_length=255)] = None


class CreateWhitelistRuleCPO(CreateWhitelistRuleBaseCPO):
    users: list[int]


class CreateWhitelistRuleExternalCPO(CreateWhitelistRuleBaseCPO):
    url: AnyHttpUrl
    auth_key: str | None = None
    auth_value: str | None = None

    @model_validator(mode="after")
    def validate_key_value(self) -> Self:
        if bool(self.auth_key) != bool(self.auth_value):
            raise ValueError(
                "Both auth_key and auth_value must be specified or omitted"
            )

        return self


class UpdateWhitelistRuleCPO(CreateWhitelistRuleCPO):
    is_enabled: bool


class UpdateWhitelistRuleExternalCPO(CreateWhitelistRuleExternalCPO):
    is_enabled: bool


class WhitelistRuleFDO(BaseFDO, WhitelistRuleDTO):
    ...


class WhitelistRuleExternalFDO(BaseFDO, WhitelistRuleExternalDTO):
    ...


class WhitelistRuleUsersFDO(WhitelistRuleCPO):
    ...
