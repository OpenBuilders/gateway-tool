from core.models import StickerCharacter
from core.services.base import BaseService


class StickerCharacterService(BaseService):
    def get(self, character_id: int) -> StickerCharacter:
        return (
            self.db_session.query(StickerCharacter)
            .filter(StickerCharacter.id == character_id)
            .one()
        )

    def get_all(self, collection_id: int | None = None) -> list[StickerCharacter]:
        query = self.db_session.query(StickerCharacter)
        if collection_id is not None:
            query = query.filter(StickerCharacter.collection_id == collection_id)

        return query.all()

    def create(
        self,
        character_id: int,
        collection_id: int,
        name: str,
        description: str,
        supply: int,
        logo_url: str | None,
    ) -> StickerCharacter:
        new_character = StickerCharacter(
            external_id=character_id,
            collection_id=collection_id,
            name=name,
            description=description,
            supply=supply,
            logo_url=logo_url,
        )
        self.db_session.add(new_character)
        self.db_session.commit()
        return new_character

    @staticmethod
    def is_update_required(
        character: StickerCharacter,
        name: str,
        description: str,
        supply: int,
        logo_url: str | None,
    ) -> bool:
        return any(
            [
                character.name != name,
                character.description != description,
                character.supply != supply,
                character.logo_url != logo_url,
            ]
        )

    def update(
        self,
        character: StickerCharacter,
        name: str,
        description: str,
        supply: int,
        logo_url: str | None,
    ) -> StickerCharacter:
        character.name = name
        character.description = description
        character.supply = supply
        character.logo_url = logo_url
        self.db_session.commit()
        return character
