from typing import Self

from pydantic import BaseModel

from core.dtos.chat.rule import ChatEligibilityRuleDTO, EligibilityCheckType
from core.dtos.chat.rule.internal import EligibilitySummaryJettonInternalDTO
from core.enums.jetton import CurrencyCategory
from core.models.rule import TelegramChatJetton


class BaseTelegramChatJettonRuleDTO(BaseModel):
    address: str
    category: CurrencyCategory | None
    threshold: int
    is_enabled: bool


class CreateTelegramChatJettonRuleDTO(BaseTelegramChatJettonRuleDTO):
    chat_id: int
    group_id: int


class UpdateTelegramChatJettonRuleDTO(BaseTelegramChatJettonRuleDTO):
    ...


class JettonEligibilityRuleDTO(ChatEligibilityRuleDTO):
    @classmethod
    def from_jetton_rule(cls, jetton_rule: TelegramChatJetton) -> Self:
        return cls(
            id=jetton_rule.id,
            group_id=jetton_rule.group_id,
            type=EligibilityCheckType.JETTON,
            title=jetton_rule.jetton.symbol,
            expected=jetton_rule.threshold,
            photo_url=jetton_rule.jetton.logo_path,
            blockchain_address=jetton_rule.jetton.address,
            is_enabled=jetton_rule.is_enabled,
            category=jetton_rule.category,
        )


class JettonEligibilitySummaryDTO(JettonEligibilityRuleDTO):
    actual: float | None = None
    is_eligible: bool = False

    @classmethod
    def from_internal_dto(cls, internal_dto: EligibilitySummaryJettonInternalDTO):
        return cls(
            id=internal_dto.id,
            group_id=internal_dto.group_id,
            type=internal_dto.type,
            title=internal_dto.title,
            expected=internal_dto.expected,
            photo_url=internal_dto.jetton.logo_path,
            blockchain_address=internal_dto.address,
            is_enabled=internal_dto.is_enabled,
            actual=internal_dto.actual,
            is_eligible=internal_dto.is_eligible,  # type: ignore
        )
