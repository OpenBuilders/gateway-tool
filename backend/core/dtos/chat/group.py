from typing import Self

from pydantic import BaseModel

from core.models.rule import TelegramChatRuleGroup


class TelegramChatRuleGroupDTO(BaseModel):
    id: int
    chat_id: int
    order: int

    @classmethod
    def from_orm(cls, obj: TelegramChatRuleGroup) -> Self:
        return cls(
            id=obj.id,
            chat_id=obj.chat_id,
            order=obj.order,
        )
