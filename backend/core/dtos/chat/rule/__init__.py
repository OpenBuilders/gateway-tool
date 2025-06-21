import dataclasses
import enum
from typing import Self

from pydantic import BaseModel, computed_field

from core.constants import (
    PROMOTE_JETTON_TEMPLATE,
    PROMOTE_NFT_COLLECTION_TEMPLATE,
    BUY_PREMIUM_URL,
    BUY_TONCOIN_URL,
)
from core.dtos.chat import TelegramChatDTO
from core.models.rule import (
    TelegramChatJetton,
    TelegramChatNFTCollection,
    TelegramChatWhitelistExternalSource,
    TelegramChatWhitelist,
    TelegramChatPremium,
    TelegramChatStickerCollection,
    TelegramChatEmoji,
    TelegramChatGiftCollection,
)
from core.models.rule import TelegramChatToncoin


class EligibilityCheckType(enum.Enum):
    TONCOIN = "toncoin"
    JETTON = "jetton"
    NFT_COLLECTION = "nft_collection"
    EXTERNAL_SOURCE = "external_source"
    WHITELIST = "whitelist"
    PREMIUM = "premium"
    STICKER_COLLECTION = "sticker_collection"
    EMOJI = "emoji"
    GIFT_COLLECTION = "gift_collection"


@dataclasses.dataclass
class TelegramChatEligibilityRulesDTO:
    toncoin: list[TelegramChatToncoin]
    jettons: list[TelegramChatJetton]
    nft_collections: list[TelegramChatNFTCollection]
    stickers: list[TelegramChatStickerCollection]
    gifts: list[TelegramChatGiftCollection]
    premium: list[TelegramChatPremium]
    whitelist_external_sources: list[TelegramChatWhitelistExternalSource]
    whitelist_sources: list[TelegramChatWhitelist]
    emoji: list[TelegramChatEmoji]


class ChatEligibilityRuleDTO(BaseModel):
    id: int
    group_id: int
    type: EligibilityCheckType
    title: str
    expected: int
    photo_url: str | None = None
    blockchain_address: str | None = None
    is_enabled: bool
    category: str | None = None

    @computed_field
    def promote_url(self) -> str | None:
        match self.type:
            case EligibilityCheckType.JETTON:
                return PROMOTE_JETTON_TEMPLATE.format(
                    jetton_master_address=self.blockchain_address
                )
            case EligibilityCheckType.NFT_COLLECTION:
                return PROMOTE_NFT_COLLECTION_TEMPLATE.format(
                    collection_address=self.blockchain_address
                )
            case EligibilityCheckType.TONCOIN:
                return BUY_TONCOIN_URL
            case EligibilityCheckType.PREMIUM:
                return BUY_PREMIUM_URL
            case _:
                return None

    @classmethod
    def from_toncoin_rule(cls, rule: TelegramChatToncoin) -> Self:
        return cls(
            id=rule.id,
            group_id=rule.group_id,
            type=EligibilityCheckType.TONCOIN,
            title="TON",
            expected=rule.threshold,
            photo_url="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTYiIGhlaWdodD0iNTYiIHZpZXdCb3g9IjAgMCA1NiA1NiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTI4IDU2QzQzLjQ2NCA1NiA1NiA0My40NjQgNTYgMjhDNTYgMTIuNTM2IDQzLjQ2NCAwIDI4IDBDMTIuNTM2IDAgMCAxMi41MzYgMCAyOEMwIDQzLjQ2NCAxMi41MzYgNTYgMjggNTZaIiBmaWxsPSIjMDA5OEVBIi8+CjxwYXRoIGQ9Ik0zNy41NjAzIDE1LjYyNzdIMTguNDM4NkMxNC45MjI4IDE1LjYyNzcgMTIuNjk0NCAxOS40MjAyIDE0LjQ2MzIgMjIuNDg2MUwyNi4yNjQ0IDQyLjk0MDlDMjcuMDM0NSA0NC4yNzY1IDI4Ljk2NDQgNDQuMjc2NSAyOS43MzQ1IDQyLjk0MDlMNDEuNTM4MSAyMi40ODYxQzQzLjMwNDUgMTkuNDI1MSA0MS4wNzYxIDE1LjYyNzcgMzcuNTYyNyAxNS42Mjc3SDM3LjU2MDNaTTI2LjI1NDggMzYuODA2OEwyMy42ODQ3IDMxLjgzMjdMMTcuNDgzMyAyMC43NDE0QzE3LjA3NDIgMjAuMDMxNSAxNy41Nzk1IDE5LjEyMTggMTguNDM2MiAxOS4xMjE4SDI2LjI1MjRWMzYuODA5MkwyNi4yNTQ4IDM2LjgwNjhaTTM4LjUxMDggMjAuNzM5TDMyLjMxMTggMzEuODM1MUwyOS43NDE3IDM2LjgwNjhWMTkuMTE5NEgzNy41NTc5QzM4LjQxNDYgMTkuMTE5NCAzOC45MTk5IDIwLjAyOTEgMzguNTEwOCAyMC43MzlaIiBmaWxsPSJ3aGl0ZSIvPgo8L3N2Zz4K",
            blockchain_address=None,
            is_enabled=rule.is_enabled,
        )

    @classmethod
    def from_whitelist_external_rule(
        cls, external_rule: TelegramChatWhitelistExternalSource
    ) -> Self:
        return cls(
            id=external_rule.id,
            group_id=external_rule.group_id,
            type=EligibilityCheckType.EXTERNAL_SOURCE,
            title=external_rule.name,
            expected=1,
            photo_url=None,
            blockchain_address=None,
            is_enabled=external_rule.is_enabled,
        )

    @classmethod
    def from_whitelist_rule(cls, whitelist_rule: TelegramChatWhitelist) -> Self:
        return cls(
            id=whitelist_rule.id,
            group_id=whitelist_rule.group_id,
            type=EligibilityCheckType.WHITELIST,
            title=whitelist_rule.name,
            expected=1,
            photo_url=None,
            blockchain_address=None,
            is_enabled=whitelist_rule.is_enabled,
        )

    @classmethod
    def from_premium_rule(cls, rule: TelegramChatPremium) -> Self:
        return cls(
            id=rule.id,
            group_id=rule.group_id,
            type=EligibilityCheckType.PREMIUM,
            title="Telegram Premium",
            expected=1,
            photo_url=None,
            blockchain_address=None,
            is_enabled=rule.is_enabled,
        )


class ChatEligibilityRuleGroupDTO(BaseModel):
    id: int
    items: list[ChatEligibilityRuleDTO]


class TelegramChatWithRulesDTO(BaseModel):
    chat: TelegramChatDTO
    groups: list[ChatEligibilityRuleGroupDTO]
    rules: list[ChatEligibilityRuleDTO]
