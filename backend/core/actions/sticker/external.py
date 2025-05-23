import hashlib
import logging

from sqlalchemy.orm import Session

from core.actions.base import BaseAction
from core.dtos.sticker import (
    StickerDomCollectionWithCharacters,
    StickerItemDTO,
    ExternalStickerItemDTO,
)
from core.services.sticker.character import StickerCharacterService
from core.services.sticker.collection import StickerCollectionService
from core.services.sticker.item import StickerItemService
from core.services.superredis import RedisService


logger = logging.getLogger(__name__)


class ExternalStickerAction(BaseAction):
    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)
        self.sticker_collection_service = StickerCollectionService(
            db_session=db_session
        )
        self.sticker_character_service = StickerCharacterService(db_session=db_session)
        self.sticker_item_service = StickerItemService(db_session=db_session)
        self.redis_service = RedisService()

    @staticmethod
    def get_metadata_cache_key(collection_id: int) -> str:
        return f"sticker-dom::{collection_id}::ownership-metadata"

    # @staticmethod
    # def get_data_cache_key(collection_id: int) -> str:
    #     return f"sticker-dom::{collection_id}::ownership-data"

    @staticmethod
    def get_collections_cache_key() -> str:
        return "sticker-dom::collections"

    @staticmethod
    def get_collection_cache_value(
        collections: list[StickerDomCollectionWithCharacters],
    ) -> str:
        """
        Generates a hash value based on the serialized data of the provided
        collections.
        This method is used for caching purposes by converting the data to its
        JSON representation, concatenating it, and producing an SHA-256 hash.

        :param collections: A list of StickerDomCollectionWithCharacters
            instances representing the collections whose hash is to be
            generated.
        :return: A string representing the SHA-256 hash of the serialized
            collections' data.
        """
        # Get hash of the serialized collections data
        collections_raw = "".join(
            [collection.model_dump_json() for collection in collections]
        )
        hash_object = hashlib.sha256(collections_raw.encode())
        return hash_object.hexdigest()

    def map_external_data_to_internal(
        self, collection_id: int, items: list[ExternalStickerItemDTO]
    ) -> list[StickerItemDTO]:
        """
        Maps external data to internal data format for stickers by integrating external data items
        with internal user and character references. The method filters out items that lack a corresponding
        internal user or character mapping, logging the appropriate debug or warning messages in such cases.

        :param collection_id: Unique identifier for the sticker collection.
        :type collection_id: int
        :param items: List of external sticker items to be mapped to the internal format.
        :type items: list[ExternalStickerItemDTO]
        :return: A list of StickerItemDTO instances representing the mapped internal sticker items.
        :rtype: list[StickerItemDTO]
        """
        characters = self.sticker_character_service.get_all(collection_id=collection_id)
        characters_by_external_id = {
            character.external_id: character for character in characters
        }

        internally_mapped_items = []

        for item in items:
            if not (character := characters_by_external_id.get(item.character_id)):
                # There is a desynchronization between Sticker Dom and the database.
                logger.warning(
                    f"Missing character {item.character_id!r} for collection {collection_id!r}. Skipping item."
                )
                continue

            internally_mapped_items.append(
                StickerItemDTO(
                    id=item.id,
                    collection_id=collection_id,
                    character_id=character.id,
                    telegram_user_id=item.telegram_user_id,
                    instance=item.instance,
                )
            )
        return internally_mapped_items
