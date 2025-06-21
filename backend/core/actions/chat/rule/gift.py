import logging

from fastapi import HTTPException
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from core.actions.chat import ManagedChatBaseAction
from core.dtos.chat.rule.gift import (
    GiftChatEligibilityRuleDTO,
    CreateTelegramChatGiftCollectionRuleDTO,
    UpdateTelegramChatGiftCollectionRuleDTO,
)
from core.models.user import User
from core.services.chat.rule.gift import TelegramChatGiftCollectionService
from core.services.gift.item import GiftUniqueService

logger = logging.getLogger(__name__)


class TelegramChatGiftCollectionAction(ManagedChatBaseAction):
    def __init__(self, db_session: Session, requestor: User, chat_slug: str):
        super().__init__(db_session, requestor, chat_slug)
        self.service = TelegramChatGiftCollectionService(db_session)
        self.gift_unique_service = GiftUniqueService(db_session)

    async def read(self, rule_id: int) -> GiftChatEligibilityRuleDTO:
        try:
            rule = self.service.get(id_=rule_id, chat_id=self.chat.id)
        except NoResultFound:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Rule not found")

        return GiftChatEligibilityRuleDTO.from_orm(rule)

    def check_duplicates(
        self,
        chat_id: int,
        group_id: int,
        collection_slug: str | None,
        category: str | None,
        entity_id: int | None = None,
    ) -> None:
        """
        Checks for duplicates among existing rules for the given inputs. Raising an
        HTTPException if a duplicate rule (with a different ID, if `entity_id`
        is provided) is found.

        :param chat_id: The unique identifier for the chat where the rule applies.
        :param group_id: The unique identifier for the group where the rule applies.
        :param collection_slug: The slug identifying the collection; can be None if not applicable.
        :param category: The category to which the rule applies; can be None if not applicable.
        :param entity_id: Optional identifier for the specific entity to exclude from duplicate checks.

        :raises HTTPException: If a duplicate rule exists.
        """
        existing_rules = self.service.find(
            chat_id=chat_id,
            group_id=group_id,
            collection_slug=collection_slug,
            category=category,
        )
        if next(filter(lambda rule: rule.id != entity_id, existing_rules), None):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Duplicate rule already exists",
            )

    def validate_params(
        self,
        collection_slug: str | None,
        model: str | None,
        backdrop: str | None,
        pattern: str | None,
    ) -> None:
        # If the collection slug is not set or attributes are not selected – no need to validate them
        if not collection_slug or not any((model, backdrop, pattern)):
            return

        options = self.gift_unique_service.get_unique_options(
            collection_slug=collection_slug
        )

        if model and model not in options.get("models", []):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Model {model!r} is not available for the collection {collection_slug!r}.",
            )

        if backdrop and backdrop not in options.get("backdrops", []):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Backdrop {backdrop!r} is not available for the collection {collection_slug!r}.",
            )

        if pattern and pattern not in options.get("patterns", []):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Pattern {pattern!r} is not available for the collection {collection_slug!r}.",
            )

    async def create(
        self,
        group_id: int | None,
        collection_slug: str | None,
        model: str | None,
        backdrop: str | None,
        pattern: str | None,
        category: None,
        threshold: int,
    ) -> GiftChatEligibilityRuleDTO:
        group_id = self.resolve_group_id(chat_id=self.chat.id, group_id=group_id)

        self.check_duplicates(
            chat_id=self.chat.id,
            group_id=group_id,
            collection_slug=collection_slug,
            category=category,
        )
        self.validate_params(collection_slug, model, backdrop, pattern)

        new_rule = self.service.create(
            CreateTelegramChatGiftCollectionRuleDTO(
                chat_id=self.chat.id,
                group_id=group_id,
                collection_slug=collection_slug,
                model=model,
                backdrop=backdrop,
                pattern=pattern,
                threshold=threshold,
                category=category,
                is_enabled=True,
            )
        )
        logger.info(
            f"New Telegram Chat Gift Collection rule created for the chat {self.chat.id!r}."
        )
        return GiftChatEligibilityRuleDTO.from_orm(new_rule)

    async def update(
        self,
        rule_id: int,
        collection_slug: str | None,
        category: str | None,
        model: str | None,
        backdrop: str | None,
        pattern: str | None,
        threshold: int,
        is_enabled: bool,
    ) -> GiftChatEligibilityRuleDTO:
        try:
            rule = self.service.get(id_=rule_id, chat_id=self.chat.id)
        except NoResultFound:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Rule not found")

        self.check_duplicates(
            chat_id=self.chat.id,
            group_id=rule.group_id,
            collection_slug=collection_slug,
            category=category,
            entity_id=rule_id,
        )
        self.validate_params(collection_slug, model, backdrop, pattern)

        updated_rule = self.service.update(
            rule=rule,
            dto=UpdateTelegramChatGiftCollectionRuleDTO(
                collection_slug=collection_slug,
                category=category,
                threshold=threshold,
                is_enabled=is_enabled,
                model=model,
                backdrop=backdrop,
                pattern=pattern,
            ),
        )
        logger.info(
            f"Updated Telegram Chat Gift Collection rule {rule_id!r} for the chat {self.chat.id!r}."
        )
        return GiftChatEligibilityRuleDTO.from_orm(updated_rule)

    async def delete(self, rule_id: int) -> None:
        self.service.delete(
            rule_id=rule_id,
            chat_id=self.chat.id,
        )
        logger.info(
            f"Deleted Telegram Chat Gift Collection rule {rule_id!r} for the chat {self.chat.id!r}."
        )
