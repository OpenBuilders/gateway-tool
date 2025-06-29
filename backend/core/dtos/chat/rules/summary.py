from typing import Self

from pydantic import BaseModel

from core.dtos.chat import TelegramChatPovDTO
from core.dtos.chat.rules import ChatEligibilityRuleDTO
from core.dtos.chat.rules.emoji import EmojiChatEligibilitySummaryDTO
from core.dtos.chat.rules.gift import GiftChatEligibilitySummaryDTO
from core.dtos.chat.rules.internal import EligibilitySummaryInternalDTO
from core.dtos.chat.rules.jetton import JettonEligibilitySummaryDTO
from core.dtos.chat.rules.nft import NftRuleEligibilitySummaryDTO
from core.dtos.chat.rules.sticker import StickerChatEligibilitySummaryDTO


class RuleEligibilitySummaryDTO(ChatEligibilityRuleDTO):
    actual: float | None = None
    is_eligible: bool = False

    @classmethod
    def from_internal_dto(cls, internal_dto: EligibilitySummaryInternalDTO) -> Self:
        return cls(
            id=internal_dto.id,
            type=internal_dto.type,
            category=internal_dto.category,
            title=internal_dto.title,
            expected=internal_dto.expected,
            photo_url=None,
            blockchain_address=internal_dto.address,
            is_enabled=internal_dto.is_enabled,
            actual=internal_dto.actual,
            is_eligible=internal_dto.is_eligible,  # type: ignore
        )


class TelegramChatWithEligibilitySummaryDTO(BaseModel):
    chat: TelegramChatPovDTO
    rules: list[
        RuleEligibilitySummaryDTO
        | JettonEligibilitySummaryDTO
        | NftRuleEligibilitySummaryDTO
        | EmojiChatEligibilitySummaryDTO
        | StickerChatEligibilitySummaryDTO
        | GiftChatEligibilitySummaryDTO
    ]
    wallet: str | None = None
