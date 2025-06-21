from pydantic import BaseModel

from core.dtos.chat.rule import EligibilityCheckType, ChatEligibilityRuleDTO
from core.dtos.chat.rule.internal import EligibilitySummaryNftCollectionInternalDTO
from core.models.rule import TelegramChatNFTCollection
from core.enums.nft import NftCollectionAsset, NftCollectionCategoryType


class BaseTelegramChatNFTCollectionRuleDTO(BaseModel):
    address: str | None
    threshold: int
    is_enabled: bool
    category: NftCollectionCategoryType | None
    asset: NftCollectionAsset | None


class CreateTelegramChatNFTCollectionRuleDTO(BaseTelegramChatNFTCollectionRuleDTO):
    chat_id: int
    group_id: int


class UpdateTelegramChatNFTCollectionRuleDTO(BaseTelegramChatNFTCollectionRuleDTO):
    ...


class NftEligibilityRuleDTO(ChatEligibilityRuleDTO):
    asset: NftCollectionAsset | None

    @classmethod
    def from_nft_collection_rule(cls, nft_collection_rule: TelegramChatNFTCollection):
        return cls(
            id=nft_collection_rule.id,
            group_id=nft_collection_rule.group_id,
            type=EligibilityCheckType.NFT_COLLECTION,
            title=nft_collection_rule.asset
            or (
                nft_collection_rule.nft_collection.name
                if nft_collection_rule.nft_collection
                else None
            ),
            expected=nft_collection_rule.threshold,
            photo_url=(
                nft_collection_rule.nft_collection.logo_path
                if nft_collection_rule.nft_collection
                else None
            ),
            blockchain_address=(
                nft_collection_rule.nft_collection.address
                if nft_collection_rule.nft_collection
                else None
            ),
            is_enabled=nft_collection_rule.is_enabled,
            asset=NftCollectionAsset.from_string(nft_collection_rule.asset),
            category=nft_collection_rule.category,
        )


class NftRuleEligibilitySummaryDTO(NftEligibilityRuleDTO):
    actual: float | None = None
    is_eligible: bool = False

    @classmethod
    def from_internal_dto(
        cls, internal_dto: EligibilitySummaryNftCollectionInternalDTO
    ):
        return cls(
            id=internal_dto.id,
            group_id=internal_dto.group_id,
            type=internal_dto.type,
            asset=internal_dto.asset,
            category=internal_dto.category,
            title=internal_dto.title,
            expected=internal_dto.expected,
            photo_url=internal_dto.collection.logo_path,
            blockchain_address=internal_dto.address,
            is_enabled=internal_dto.is_enabled,
            actual=internal_dto.actual,
            is_eligible=internal_dto.is_eligible,  # type: ignore
        )
