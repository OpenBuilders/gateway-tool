import logging

from fastapi import HTTPException
from sqlalchemy.exc import NoResultFound, IntegrityError
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from core.actions.chat import ManagedChatBaseAction
from core.dtos.chat.rule import UpdateRuleGroupDTO
from core.enums.rule import EligibilityCheckType
from core.models.rule import (
    TelegramChatEmoji,
    TelegramChatJetton,
    TelegramChatNFTCollection,
    TelegramChatGiftCollection,
    TelegramChatStickerCollection,
    TelegramChatPremium,
    TelegramChatWhitelist,
    TelegramChatWhitelistExternalSource,
    TelegramChatToncoin,
    TelegramChatRuleBase,
)

MODEL_BY_RULE_TYPE = {
    EligibilityCheckType.EMOJI: TelegramChatEmoji,
    EligibilityCheckType.JETTON: TelegramChatJetton,
    EligibilityCheckType.NFT_COLLECTION: TelegramChatNFTCollection,
    EligibilityCheckType.GIFT_COLLECTION: TelegramChatGiftCollection,
    EligibilityCheckType.STICKER_COLLECTION: TelegramChatStickerCollection,
    EligibilityCheckType.PREMIUM: TelegramChatPremium,
    EligibilityCheckType.WHITELIST: TelegramChatWhitelist,
    EligibilityCheckType.EXTERNAL_SOURCE: TelegramChatWhitelistExternalSource,
    EligibilityCheckType.TONCOIN: TelegramChatToncoin,
}

# To prevent RuntimeError if something is missing on the mapping
for _type in EligibilityCheckType:
    if _type not in MODEL_BY_RULE_TYPE:
        raise ValueError(f"Missing model for rule type {type}")


logger = logging.getLogger(__name__)


class RuleAction(ManagedChatBaseAction):
    def move(self, item: UpdateRuleGroupDTO) -> None:
        """
        Moves a rule to a new group in a Telegram chat.

        This function updates the group ID of a specified rule in the database.
        It validates whether the rule type exists and whether the rule itself
        exists for the current Telegram chat before proceeding with the group
        change.
        If the rule is already in the target group, no action is taken.

        :param item: Rule information including rule ID, type, and target group ID.
        :return: None
        :raises HTTPException: If the rule type is unsupported or if the rule
                               is not found in the chat for the provided type.

        """
        try:
            model: type[TelegramChatRuleBase] = MODEL_BY_RULE_TYPE[item.type]
        except KeyError:
            logger.error(f"Rule type {item.type!r} not supported.")
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Rule type {item.type} not supported. Supported types: {', '.join([k.value for k in MODEL_BY_RULE_TYPE.keys()])}.",
            )

        try:
            existing_item = (
                self.db_session.query(model)
                .filter(model.id == item.rule_id, model.chat_id == self.chat.id)
                .one()
            )
        except NoResultFound:
            logger.error(
                f"Rule {item.rule_id!r} of type {item.type!r} not found in chat {self.chat.id!r}."
            )
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Rule {item.rule_id!r} of type {item.type.value!r} not found in chat {self.chat.id!r}.",
            )

        previous_group_id = existing_item.group_id

        if previous_group_id == item.group_id:
            logger.debug(
                f"Rule {item.rule_id!r} of type {item.type!r} already in group {item.group_id!r}."
            )
            return None

        try:
            new_group = self.telegram_chat_rule_group_service.get(
                chat_id=self.chat.id, group_id=item.group_id
            )
        except NoResultFound:
            logger.error(
                f"No rule group found for group ID {item.group_id!r} in chat {self.chat.id!r}."
            )
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"No rule group found for group ID {item.group_id!r} in chat {self.chat.id!r}.",
            )

        try:
            existing_item.group_id = new_group.id
            self.db_session.commit()
            logger.info(
                f"Moved rule {item.rule_id!r} of type {item.type!r} for chat {self.chat.id!r} to group {new_group.id!r}."
            )
        except IntegrityError:
            logger.error(
                f"No rule group found for group ID {new_group.id!r} in chat {self.chat.id!r}."
            )
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"No rule group found for group ID {new_group.id!r} in chat {self.chat.id!r}.",
            )

        self.remove_group_if_empty(group_id=previous_group_id)

        return None
