import logging

from core.models.rule import (
    TelegramChatJetton,
    TelegramChatNFTCollection,
    TelegramChatToncoin,
)
from core.services.chat.rule.base import BaseTelegramChatRuleService

logger = logging.getLogger(__name__)


class TelegramChatJettonService(BaseTelegramChatRuleService[TelegramChatJetton]):
    model = TelegramChatJetton


class TelegramChatNFTCollectionService(
    BaseTelegramChatRuleService[TelegramChatNFTCollection]
):
    model = TelegramChatNFTCollection


class TelegramChatToncoinService(BaseTelegramChatRuleService[TelegramChatToncoin]):
    model = TelegramChatToncoin
