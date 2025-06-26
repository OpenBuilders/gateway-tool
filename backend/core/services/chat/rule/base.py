import logging
from abc import ABC
from typing import Any, Generic, TypeVar

from sqlalchemy import desc

from core.dtos.chat.rule.emoji import (
    CreateTelegramChatEmojiRuleDTO,
    UpdateTelegramChatEmojiRuleDTO,
)
from core.dtos.chat.rule.gift import (
    CreateTelegramChatGiftCollectionRuleDTO,
    UpdateTelegramChatGiftCollectionRuleDTO,
)
from core.dtos.chat.rule.jetton import (
    CreateTelegramChatJettonRuleDTO,
    UpdateTelegramChatJettonRuleDTO,
)
from core.dtos.chat.rule.nft import (
    CreateTelegramChatNFTCollectionRuleDTO,
    UpdateTelegramChatNFTCollectionRuleDTO,
)
from core.dtos.chat.rule.premium import (
    CreateTelegramChatPremiumRuleDTO,
    UpdateTelegramChatPremiumRuleDTO,
)
from core.dtos.chat.rule.sticker import (
    CreateTelegramChatStickerCollectionRuleDTO,
    UpdateTelegramChatStickerCollectionRuleDTO,
)
from core.dtos.chat.rule.toncoin import (
    CreateTelegramChatToncoinRuleDTO,
    UpdateTelegramChatToncoinRuleDTO,
)
from core.dtos.chat.rule.whitelist import (
    CreateTelegramChatWhitelistExternalSourceDTO,
    UpdateTelegramChatWhitelistExternalSourceDTO,
    CreateTelegramChatWhitelistDTO,
    UpdateTelegramChatWhitelistDTO,
)
from core.models.rule import (
    TelegramChatRuleBase,
)
from core.services.base import BaseService


logger = logging.getLogger(__name__)

CreateTelegramChatRuleDTOType = (
    CreateTelegramChatJettonRuleDTO
    | CreateTelegramChatNFTCollectionRuleDTO
    | CreateTelegramChatToncoinRuleDTO
    | CreateTelegramChatStickerCollectionRuleDTO
    | CreateTelegramChatGiftCollectionRuleDTO
    | CreateTelegramChatPremiumRuleDTO
    | CreateTelegramChatEmojiRuleDTO
    | CreateTelegramChatWhitelistExternalSourceDTO
    | CreateTelegramChatWhitelistDTO
)
UpdateTelegramChatRuleDTOType = (
    UpdateTelegramChatJettonRuleDTO
    | UpdateTelegramChatNFTCollectionRuleDTO
    | UpdateTelegramChatToncoinRuleDTO
    | UpdateTelegramChatStickerCollectionRuleDTO
    | UpdateTelegramChatGiftCollectionRuleDTO
    | UpdateTelegramChatPremiumRuleDTO
    | UpdateTelegramChatEmojiRuleDTO
    | UpdateTelegramChatWhitelistExternalSourceDTO
    | UpdateTelegramChatWhitelistDTO
)

TelegramChatRuleT = TypeVar("TelegramChatRuleT", bound=TelegramChatRuleBase)


class BaseTelegramChatRuleService(BaseService, ABC, Generic[TelegramChatRuleT]):
    model: TelegramChatRuleT

    def create(self, dto: CreateTelegramChatRuleDTOType) -> TelegramChatRuleT:
        new_rule = self.model(**dto.model_dump())  # noqa
        self.db_session.add(new_rule)
        self.db_session.commit()
        logger.debug(f"Telegram Chat Rule {new_rule!r} created.")
        return new_rule

    def get(self, id_: int, chat_id: int) -> TelegramChatRuleT:
        return (
            self.db_session.query(self.model)
            .filter(self.model.id == id_, self.model.chat_id == chat_id)
            .one()
        )

    def find(self, **params: Any) -> list[type[TelegramChatRuleT]]:
        """
        Find records in the database table based on filter parameters provided as a dictionary.

        This method allows querying the database using parameters corresponding to column names in
        the model's table. Invalid parameters (not matching any column in the table) will raise an
        exception. The method filters records based on these valid parameters and returns a list
        of results.

        :param params: kwargs containing column names as keys and filter values as values.
                       Only valid column names of the model table are allowed.
        :return: A list of records filtered by the provided parameters.
        :raises AttributeError: If any of the specified keys in `params` does not match any column
                                 name of the model's table.
        """
        for param in params.keys():
            if param not in self.model.__table__.columns.keys():
                raise AttributeError(f"Invalid parameter {param!r}.")

        return self.db_session.query(self.model).filter_by(**params).all()

    def update(
        self,
        rule: TelegramChatRuleT,
        dto: UpdateTelegramChatRuleDTOType,
    ) -> TelegramChatRuleT:
        for key, value in dto.model_dump(exclude_unset=True).items():
            setattr(rule, key, value)
        self.db_session.commit()
        logger.debug(f"{rule!r} updated.")
        return rule

    def get_all(
        self, chat_id: int | None = None, enabled_only: bool = True
    ) -> list[TelegramChatRuleT]:
        query = self.db_session.query(self.model)
        if chat_id is not None:
            query = query.filter(self.model.chat_id == chat_id)

        if enabled_only:
            query = query.filter(self.model.is_enabled.is_(True))

        query = query.order_by(desc(self.model.is_enabled), self.model.created_at)
        return query.all()

    def delete(self, rule_id: int, chat_id: int) -> None:
        self.db_session.query(self.model).filter(
            self.model.id == rule_id, self.model.chat_id == chat_id
        ).delete(synchronize_session="fetch")
        self.db_session.commit()
        logger.debug(
            f"Telegram Chat Rule {self.model.__name__!r} {rule_id=!r} deleted."
        )
