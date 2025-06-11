from typing import Self

from core.dtos.chat.rules import ChatEligibilityRuleDTO, EligibilityCheckType
from core.dtos.chat.rules.internal import EligibilitySummaryInternalDTO
from core.models.rule import TelegramChatEmoji


class EmojiChatEligibilityRuleDTO(ChatEligibilityRuleDTO):
    emoji_id: str

    @classmethod
    def from_orm(cls, obj: TelegramChatEmoji) -> Self:
        return cls(
            id=obj.id,
            type=EligibilityCheckType.EMOJI,
            title=obj.emoji_id,
            expected=1,
            photo_url=obj.logo_url,
            blockchain_address=None,
            is_enabled=obj.is_enabled,
            emoji_id=obj.emoji_id,
        )


class EmojiChatEligibilitySummaryDTO(EmojiChatEligibilityRuleDTO):
    actual: int | None = None
    is_eligible: bool = False

    @classmethod
    def from_internal_dto(cls, internal_dto: EligibilitySummaryInternalDTO):
        return cls(
            id=internal_dto.id,
            type=internal_dto.type,
            title=internal_dto.title,
            emoji_id=internal_dto.title,
            expected=internal_dto.expected,
            photo_url=None,
            blockchain_address=None,
            is_enabled=internal_dto.is_enabled,
            actual=internal_dto.actual,
            is_eligible=internal_dto.is_eligible,  # type: ignore
        )
