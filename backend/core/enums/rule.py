import enum


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
