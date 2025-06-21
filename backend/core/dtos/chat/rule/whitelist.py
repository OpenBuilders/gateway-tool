import datetime
from functools import cached_property
from typing import Self

from pydantic import BaseModel

from core.dtos.chat.rule import EligibilityCheckType
from core.models.rule import TelegramChatWhitelistExternalSource, TelegramChatWhitelist


class TelegramChatWhitelistExternalSourceDTO(BaseModel):
    external_source_url: str
    name: str
    description: str | None
    auth_key: str | None
    auth_value: str | None
    is_enabled: bool


class CreateTelegramChatWhitelistExternalSourceDTO(
    TelegramChatWhitelistExternalSourceDTO
):
    chat_id: int
    group_id: int


class UpdateTelegramChatWhitelistExternalSourceDTO(
    TelegramChatWhitelistExternalSourceDTO
):
    ...


class TelegramChatWhitelistDTO(BaseModel):
    name: str
    description: str | None
    is_enabled: bool


class CreateTelegramChatWhitelistDTO(TelegramChatWhitelistDTO):
    chat_id: int
    group_id: int


class UpdateTelegramChatWhitelistDTO(TelegramChatWhitelistDTO):
    ...


class WhitelistRuleItemsDifferenceDTO(BaseModel):
    previous: list[int] | None
    current: list[int]

    @cached_property
    def removed(self) -> list[int]:
        if not self.previous:
            return []
        return list(set(self.previous) - set(self.current))

    @cached_property
    def added(self) -> list[int]:
        if not self.previous:
            return self.current
        return list(set(self.current) - set(self.previous))


class WhitelistRuleCPO(BaseModel):
    users: list[int]


class BaseWhitelistRuleDTO(BaseModel):
    id: int
    type: EligibilityCheckType
    chat_id: int
    name: str
    description: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_enabled: bool
    users: list[int] | None = None


class WhitelistRuleDTO(BaseWhitelistRuleDTO):
    @classmethod
    def from_orm(cls, obj: TelegramChatWhitelist) -> Self:
        return cls(
            id=obj.id,
            type=EligibilityCheckType.WHITELIST,
            chat_id=obj.chat_id,
            name=obj.name,
            description=obj.description,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            is_enabled=obj.is_enabled,
            users=obj.content,
        )


class WhitelistRuleExternalDTO(BaseWhitelistRuleDTO):
    url: str
    auth_key: str | None
    auth_value: str | None

    @classmethod
    def from_orm(cls, obj: TelegramChatWhitelistExternalSource) -> Self:
        return cls(
            id=obj.id,
            type=EligibilityCheckType.EXTERNAL_SOURCE,
            chat_id=obj.chat_id,
            url=obj.url,
            name=obj.name,
            description=obj.description,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            is_enabled=obj.is_enabled,
            users=obj.content,
            auth_key=obj.auth_key,
            auth_value=obj.auth_value,
        )
