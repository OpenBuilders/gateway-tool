from typing import Iterable

from core.models.sticker import StickerItem
from core.services.base import BaseService


class StickerItemService(BaseService):
    def get(self, item_id: str) -> StickerItem:
        return (
            self.db_session.query(StickerItem).filter(StickerItem.id == item_id).one()
        )

    def get_all(
        self,
        telegram_user_id: int | None = None,
        collection_id: int | None = None,
        character_id: int | None = None,
        item_ids: Iterable[str] | None = None,
    ) -> list[StickerItem]:
        query = self.db_session.query(StickerItem)
        if telegram_user_id is not None:
            query = query.filter(StickerItem.telegram_user_id == telegram_user_id)
        if collection_id is not None:
            query = query.filter(StickerItem.collection_id == collection_id)
        if character_id is not None:
            query = query.filter(StickerItem.character_id == character_id)
        if item_ids is not None:
            query = query.filter(StickerItem.id.in_(item_ids))

        return query.all()

    def create(
        self,
        item_id: str,
        instance: int,
        collection_id: int,
        character_id: int,
        telegram_user_id: int,
    ) -> StickerItem:
        new_item = StickerItem(
            id=item_id,
            instance=instance,
            collection_id=collection_id,
            character_id=character_id,
            telegram_user_id=telegram_user_id,
        )
        self.db_session.add(new_item)
        self.db_session.commit()
        return new_item

    def update(
        self,
        item: StickerItem,
        telegram_user_id: int,
    ) -> StickerItem:
        item.telegram_user_id = telegram_user_id
        self.db_session.commit()
        return item

    def delete(self, item_id: str) -> None:
        self.db_session.query(StickerItem).filter(StickerItem.id == item_id).delete(
            synchronize_session="fetch"
        )

    def bulk_delete(
        self,
        item_ids: Iterable[str],
    ) -> None:
        self.db_session.query(StickerItem).filter(StickerItem.id.in_(item_ids)).delete(
            synchronize_session="fetch"
        )
