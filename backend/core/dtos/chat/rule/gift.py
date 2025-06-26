from typing import Self

from pydantic import BaseModel, model_validator, computed_field

from core.dtos.chat.rule import ChatEligibilityRuleDTO
from core.enums.rule import EligibilityCheckType
from core.dtos.chat.rule.internal import EligibilitySummaryGiftCollectionInternalDTO
from core.dtos.gift.collection import GiftCollectionDTO
from core.models.rule import TelegramChatGiftCollection


class BaseTelegramChatGiftCollectionRuleDTO(BaseModel):
    threshold: int
    is_enabled: bool
    collection_slug: str | None
    model: str | None
    backdrop: str | None
    pattern: str | None
    category: str | None

    @model_validator(mode="after")
    def validate_slug_or_category(self) -> Self:
        if (self.category is None) == (self.collection_slug is None):
            raise ValueError(
                "Either category or collection_slug must be provided and not both."
            )

        return self


class CreateTelegramChatGiftCollectionRuleDTO(BaseTelegramChatGiftCollectionRuleDTO):
    chat_id: int
    group_id: int


class UpdateTelegramChatGiftCollectionRuleDTO(BaseTelegramChatGiftCollectionRuleDTO):
    ...


class GiftChatEligibilityRuleDTO(ChatEligibilityRuleDTO):
    collection: GiftCollectionDTO | None
    model: str | None
    backdrop: str | None
    pattern: str | None

    @classmethod
    def from_orm(cls, obj: TelegramChatGiftCollection) -> Self:
        return cls(
            id=obj.id,
            group_id=obj.group_id,
            type=EligibilityCheckType.GIFT_COLLECTION,
            title=obj.collection.title if obj.collection else obj.category,
            expected=obj.threshold,
            photo_url=obj.collection.preview_url,
            blockchain_address=None,
            is_enabled=obj.is_enabled,
            collection=GiftCollectionDTO.from_orm(obj.collection)
            if obj.collection
            else None,
            category=obj.category,
            model=obj.model,
            pattern=obj.pattern,
            backdrop=obj.backdrop,
        )


class GiftChatEligibilitySummaryDTO(GiftChatEligibilityRuleDTO):
    actual: int | None = None
    is_eligible: bool = False

    @computed_field
    def promote_url(self) -> str | None:
        # FIXME: Turn on when market is released
        # if self.collection:
        #     return PROMOTE_GIFT_COLLECTION_TEMPLATE.format(
        #         collection_slug=self.collection.slug
        #     )

        return None

    @classmethod
    def from_internal_dto(
        cls, internal_dto: EligibilitySummaryGiftCollectionInternalDTO
    ) -> Self:
        return cls(
            id=internal_dto.id,
            group_id=internal_dto.group_id,
            type=internal_dto.type,
            category=internal_dto.category,
            title=internal_dto.title,
            expected=internal_dto.expected,
            photo_url=internal_dto.collection.preview_url,
            blockchain_address=internal_dto.address,
            is_enabled=internal_dto.is_enabled,
            actual=internal_dto.actual,
            is_eligible=internal_dto.is_eligible,  # type: ignore
            collection=internal_dto.collection,
            model=internal_dto.model,
            pattern=internal_dto.pattern,
            backdrop=internal_dto.backdrop,
        )
