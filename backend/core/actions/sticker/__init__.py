import logging
from collections import defaultdict

from sqlalchemy.exc import NoResultFound

from core.actions.base import BaseAction
from core.dtos.sticker import (
    StickerCollectionDTO,
    MinimalStickerCollectionWithCharactersDTO,
    StickerCharacterDTO,
    MinimalStickerCharacterDTO,
)
from core.exceptions.sticker import (
    StickerCollectionNotFound,
    StickerCharacterNotFound,
)
from core.services.sticker.character import StickerCharacterService
from core.services.sticker.collection import StickerCollectionService


logger = logging.getLogger(__name__)


class StickerCollectionAction(BaseAction):
    def __init__(self, db_session) -> None:
        super().__init__(db_session)
        self.sticker_collection_service = StickerCollectionService(db_session)

    def get_all(self) -> list[StickerCollectionDTO]:
        collections = self.sticker_collection_service.get_all()
        return [StickerCollectionDTO.from_orm(collection) for collection in collections]

    def create(self, dto: StickerCollectionDTO) -> StickerCollectionDTO:
        collection = self.sticker_collection_service.create(
            collection_id=dto.id,
            title=dto.title,
            description=dto.description,
            logo_url=dto.logo_url,
        )
        return StickerCollectionDTO.from_orm(collection)

    def get(self, collection_id: int) -> StickerCollectionDTO:
        try:
            collection = self.sticker_collection_service.get(collection_id)
        except NoResultFound:
            raise StickerCollectionNotFound(
                f"No sticker collection with id {collection_id!r} found."
            )
        return StickerCollectionDTO.from_orm(collection)

    def get_or_create(self, dto: StickerCollectionDTO) -> StickerCollectionDTO:
        try:
            return self.get(dto.id)
        except StickerCollectionNotFound:
            return self.create(dto)


class StickerCharacterAction(BaseAction):
    def __init__(self, db_session) -> None:
        super().__init__(db_session)
        self.sticker_character_service = StickerCharacterService(db_session)

    def get_all(self, collection_id: int | None) -> list[StickerCharacterDTO]:
        characters = self.sticker_character_service.get_all(collection_id=collection_id)
        return [StickerCharacterDTO.from_orm(character) for character in characters]

    async def get_all_grouped(self) -> list[MinimalStickerCollectionWithCharactersDTO]:
        """
        Asynchronously retrieves all sticker collections grouped by their respective
        characters.
        Each collection includes a list of characters sorted by their names,
        while the collections themselves are sorted by their titles.

        :return: A list of `MinimalStickerCollectionWithCharactersDTO` objects
            representing grouped sticker collections with nested characters.
        """
        characters = self.sticker_character_service.get_all()
        characters_by_collection = defaultdict(list)
        for character in characters:
            characters_by_collection[character.collection].append(character)
        return [
            MinimalStickerCollectionWithCharactersDTO(
                id=collection.id,
                title=collection.title,
                logo_url=collection.logo_url,
                characters=[
                    MinimalStickerCharacterDTO.from_orm(character)
                    for character in sorted(characters, key=lambda ch: ch.name)
                ],
            )
            for collection, characters in sorted(
                characters_by_collection.items(), key=lambda c_tuple: c_tuple[0].title
            )
        ]

    def create(self, dto: StickerCharacterDTO) -> StickerCharacterDTO:
        sticker_character = self.sticker_character_service.create(
            character_id=dto.id,
            collection_id=dto.collection_id,
            name=dto.name,
            description=dto.description,
            supply=dto.supply,
            logo_url=dto.logo_url,
        )
        return StickerCharacterDTO.from_orm(sticker_character)

    def get(self, character_id: int) -> StickerCharacterDTO:
        try:
            character = self.sticker_character_service.get(character_id)
        except NoResultFound:
            raise StickerCharacterNotFound(
                f"No sticker character with id {character_id!r} found."
            )
        return StickerCharacterDTO.from_orm(character)

    def get_or_create(self, dto: StickerCharacterDTO) -> StickerCharacterDTO:
        try:
            return self.get(dto.id)
        except StickerCharacterNotFound:
            return self.create(dto)
