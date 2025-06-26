from pydantic import BaseModel


class TelegramChatPremiumRule(BaseModel):
    is_enabled: bool


class CreateTelegramChatPremiumRuleDTO(TelegramChatPremiumRule):
    chat_id: int
    group_id: int


class UpdateTelegramChatPremiumRuleDTO(TelegramChatPremiumRule):
    ...
