from pydantic import BaseModel

from core.enums.jetton import CurrencyCategory


class BaseTelegramChatToncoinRuleDTO(BaseModel):
    category: CurrencyCategory | None
    threshold: int
    is_enabled: bool


class CreateTelegramChatToncoinRuleDTO(BaseTelegramChatToncoinRuleDTO):
    chat_id: int
    group_id: int


class UpdateTelegramChatToncoinRuleDTO(BaseTelegramChatToncoinRuleDTO):
    ...
