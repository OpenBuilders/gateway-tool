from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.actions.chat import ManagedChatBaseAction
from core.dtos.chat.group import TelegramChatRuleGroupDTO
from core.models.user import User
from core.services.chat.rule.group import TelegramChatRuleGroupService


class TelegramChatRuleGroupAction(ManagedChatBaseAction):
    def __init__(
        self, db_session: Session, requestor: User, chat_slug: str, **kwargs
    ) -> None:
        super().__init__(
            db_session=db_session, requestor=requestor, chat_slug=chat_slug
        )
        self.service = TelegramChatRuleGroupService(db_session)

    def create(self) -> TelegramChatRuleGroupDTO:
        group = self.service.create(chat_id=self.chat.id)
        return TelegramChatRuleGroupDTO.from_orm(group)

    def delete(self, group_id: int) -> None:
        groups = self.service.get_all(chat_id=self.chat.id)
        if group_id not in {group.id for group in groups}:
            raise HTTPException(
                detail="Group not found",
                status_code=404,
            )
        elif len(groups) == 1:
            raise HTTPException(
                detail="Cannot delete the only group",
                status_code=400,
            )

        self.service.delete(chat_id=self.chat.id, group_id=group_id)
