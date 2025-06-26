from pydantic import BaseModel, computed_field

from core.enums.rule import EligibilityCheckType
from core.dtos.gift.collection import GiftCollectionDTO
from core.dtos.resource import NftCollectionDTO, JettonDTO
from core.dtos.sticker import MinimalStickerCollectionDTO, MinimalStickerCharacterDTO
from core.enums.nft import NftCollectionAsset


class EligibilitySummaryInternalDTO(BaseModel):
    """
    Used for internal purposes to check if chat is eligible for promotion
    """

    id: int
    group_id: int
    type: EligibilityCheckType
    title: str
    address_raw: str | None = None  # required for blockchain rules only
    actual: float | int = 0.0
    expected: float | int
    is_enabled: bool
    category: str | None = None

    @property
    def address(self):
        if not self.address_raw:
            return None
        return self.address_raw

    @computed_field(return_type=bool)
    def is_eligible(self) -> bool:
        return self.actual >= self.expected

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} "
            f"{self.type} "
            f"{self.category=} "
            f"{self.title=} "
            f"{self.address=} "
            f"{self.actual=} "
            f"{self.expected=}>"
        )


class EligibilitySummaryJettonInternalDTO(EligibilitySummaryInternalDTO):
    jetton: JettonDTO


class EligibilitySummaryNftCollectionInternalDTO(EligibilitySummaryInternalDTO):
    asset: NftCollectionAsset | None = None
    collection: NftCollectionDTO


class EligibilitySummaryGiftCollectionInternalDTO(EligibilitySummaryInternalDTO):
    collection: GiftCollectionDTO | None
    model: str | None
    backdrop: str | None
    pattern: str | None


class EligibilitySummaryStickerCollectionInternalDTO(EligibilitySummaryInternalDTO):
    collection: MinimalStickerCollectionDTO | None
    character: MinimalStickerCharacterDTO | None


class RulesEligibilityGroupSummaryInternalDTO(BaseModel):
    """
    Represents a summary of eligibility groups consisting of multiple eligibility
    summary items.

    This class acts as a container for a list of eligibility summary items and
    provides utility methods to evaluate their collective eligibility state.
    """

    id: int
    items: list[EligibilitySummaryInternalDTO]

    def __bool__(self):
        # If there are no items on the list - user should not be eligible for that empty group
        if not self.items:
            return False

        return all(item.is_eligible for item in self.items)

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.items=})>"


class RulesEligibilitySummaryInternalDTO(BaseModel):
    """
    Represents a summary of rule eligibility along with associated wallet details.

    The class is designed to encapsulate multiple groups of rule eligibility
    summaries and provide aggregated access to their items. It provides boolean
    context for determining overall eligibility and a string representation of
    its contents.
    """

    groups: list[RulesEligibilityGroupSummaryInternalDTO]
    wallet: str | None = None

    @property
    def items(self) -> list[EligibilitySummaryInternalDTO]:
        return [item for group in self.groups for item in group.items]

    def __bool__(self):
        return any(bool(group) for group in self.groups)

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.items=})>"
