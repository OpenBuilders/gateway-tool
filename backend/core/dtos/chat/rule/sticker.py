from typing import Self

from pydantic import BaseModel, computed_field

from core.constants import PROMOTE_STICKER_COLLECTION_TEMPLATE
from core.dtos.chat.rule import ChatEligibilityRuleDTO
from core.enums.rule import EligibilityCheckType
from core.dtos.chat.rule.internal import EligibilitySummaryStickerCollectionInternalDTO
from core.dtos.sticker import MinimalStickerCollectionDTO, MinimalStickerCharacterDTO
from core.models.rule import TelegramChatStickerCollection


class BaseTelegramChatStickerCollectionRuleDTO(BaseModel):
    threshold: int
    is_enabled: bool
    collection_id: int | None
    character_id: int | None
    category: str | None


class CreateTelegramChatStickerCollectionRuleDTO(
    BaseTelegramChatStickerCollectionRuleDTO
):
    chat_id: int
    group_id: int


class UpdateTelegramChatStickerCollectionRuleDTO(
    BaseTelegramChatStickerCollectionRuleDTO
):
    ...


class StickerChatEligibilityRuleDTO(ChatEligibilityRuleDTO):
    collection: MinimalStickerCollectionDTO | None
    character: MinimalStickerCharacterDTO | None

    @computed_field
    def promote_url(self) -> str | None:
        if self.collection:
            return PROMOTE_STICKER_COLLECTION_TEMPLATE.format(
                collection_id=self.collection.id
            )

        return None

    @classmethod
    def from_orm(cls, obj: TelegramChatStickerCollection) -> Self:
        return cls(
            id=obj.id,
            group_id=obj.group_id,
            type=EligibilityCheckType.STICKER_COLLECTION,
            title=(
                obj.category
                or (obj.character.name if obj.character else None)
                or (obj.collection.title if obj.collection else None)
            ),
            expected=obj.threshold,
            photo_url=obj.collection.logo_url,
            blockchain_address=None,
            is_enabled=obj.is_enabled,
            collection=MinimalStickerCollectionDTO.from_orm(obj.collection)
            if obj.collection
            else None,
            character=MinimalStickerCharacterDTO.from_orm(obj.character)
            if obj.character
            else None,
        )


class StickerChatEligibilitySummaryDTO(StickerChatEligibilityRuleDTO):
    actual: int | None = None
    is_eligible: bool = False

    @classmethod
    def from_internal_dto(
        cls, internal_dto: EligibilitySummaryStickerCollectionInternalDTO
    ) -> Self:
        return cls(
            id=internal_dto.id,
            group_id=internal_dto.group_id,
            type=internal_dto.type,
            category=internal_dto.category,
            title=internal_dto.title,
            expected=internal_dto.expected,
            photo_url=internal_dto.character.logo_url
            if internal_dto.character
            else internal_dto.collection.logo_url,
            blockchain_address=internal_dto.address,
            is_enabled=internal_dto.is_enabled,
            actual=internal_dto.actual,
            is_eligible=internal_dto.is_eligible,  # type: ignore
            collection=internal_dto.collection,
            character=internal_dto.character,
        )
