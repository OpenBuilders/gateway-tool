from core.db import Base

from core.models.blockchain import Jetton, NFTCollection, NftItem  # noqa
from core.models.chat import (  # noqa
    TelegramChat,
    TelegramChatUser,
)
from core.models.gift import GiftCollection, GiftUnique  # noqa
from core.models.rule import (  # noqa
    TelegramChatRuleGroup,
    TelegramChatJetton,
    TelegramChatNFTCollection,
    TelegramChatToncoin,
    TelegramChatWhitelist,
    TelegramChatWhitelistExternalSource,
    TelegramChatStickerCollection,
    TelegramChatEmoji,
    TelegramChatPremium,
    TelegramChatGiftCollection,
)
from core.models.sticker import StickerCollection, StickerCharacter, StickerItem  # noqa
from core.models.user import User  # noqa
from core.models.wallet import UserWallet, JettonWallet, TelegramChatUserWallet  # noqa


# To prevent imports from this module
# Only Base should be imported from this module to import models by migrator
__all__ = ["Base"]
