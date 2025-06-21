import logging

from pytonapi.schema.nft import NftItem as TONNftItem, NftItems
from sqlalchemy import desc
from sqlalchemy.exc import NoResultFound

from core.models.blockchain import NFTCollection, NftItem
from core.dtos.resource import (
    NftItemMetadataDTO,
    NftCollectionMetadataDTO,
    NftCollectionDTO,
)
from core.services.base import BaseService


logger = logging.getLogger(__name__)


class NftCollectionService(BaseService):
    def create(
        self,
        dto: NftCollectionDTO,
    ) -> NFTCollection:
        nft = NFTCollection(
            address=dto.address,
            name=dto.name,
            description=dto.description,
            logo_path=dto.logo_path,
            blockchain_metadata=dto.blockchain_metadata,
            is_enabled=dto.is_enabled,
        )
        self.db_session.add(nft)
        self.db_session.commit()
        logger.info(f"NFT Collection {nft.name!r} created.")
        return nft

    def update(
        self,
        nft_collection: NFTCollection,
        dto: NftCollectionDTO,
    ) -> NFTCollection:
        nft_collection.name = dto.name
        nft_collection.description = dto.description
        nft_collection.logo_path = dto.logo_path
        nft_collection.blockchain_metadata = dto.blockchain_metadata
        nft_collection.is_enabled = dto.is_enabled
        self.db_session.commit()
        logger.info(f"NFT Collection {nft_collection.name!r} updated.")
        return nft_collection

    def update_metadata(
        self, address: str, blockchain_metadata: NftCollectionMetadataDTO
    ) -> NFTCollection:
        nft_collection = self.get(address=address)
        nft_collection.blockchain_metadata = blockchain_metadata
        self.db_session.commit()
        logger.info(f"NFT Collection {nft_collection.name!r} metadata updated.")
        return nft_collection

    def update_status(self, address: str, is_enabled: bool) -> NFTCollection:
        nft_collection = self.get(address=address)
        nft_collection.is_enabled = is_enabled
        self.db_session.commit()
        logger.info(f"NFT Collection {nft_collection.name!r} status updated.")
        return nft_collection

    def get(self, address: str) -> NFTCollection:
        return (
            self.db_session.query(NFTCollection)
            .filter(NFTCollection.address == address)
            .one()
        )

    def get_whitelisted(self) -> list[NFTCollection]:
        return (
            self.db_session.query(NFTCollection)
            .filter(NFTCollection.is_enabled.is_(True))
            .all()
        )

    def get_all(self, whitelisted_only: bool) -> list[NFTCollection]:
        query = self.db_session.query(NFTCollection)
        if whitelisted_only:
            query = query.filter(NFTCollection.is_enabled.is_(True))
        return query.order_by(
            desc(NFTCollection.is_enabled), NFTCollection.created_at
        ).all()

    def count(self) -> int:
        return self.db_session.query(NFTCollection).count()


class NftItemService(BaseService):
    def _create(self, nft_item: TONNftItem) -> NftItem:
        nft = NftItem(
            address=nft_item.address.to_raw(),
            owner_address=nft_item.owner.address.to_raw(),
            collection_address=nft_item.collection.address.to_raw(),
            blockchain_metadata=NftItemMetadataDTO.from_nft_item(nft_item),
        )
        self.db_session.add(nft)
        logger.info(f"NFT Item {nft.address!r} created.")
        return nft

    def _update(self, nft_item: TONNftItem, nft: NftItem) -> NftItem:
        """The only updatable field is the owner address."""
        if nft_item.owner.address.to_raw() == nft.owner_address:
            logger.info(f"NFT Item {nft.address!r} owner address unchanged.")
            return nft

        nft.owner_address = nft_item.owner.address.to_raw()
        nft.blockchain_metadata = NftItemMetadataDTO.from_nft_item(nft_item)
        self.db_session.add(nft)
        logger.info(f"NFT Item {nft.address!r} updated.")
        return nft

    def create_or_update(self, nft_item: TONNftItem) -> NftItem:
        try:
            nft = self.get(address=nft_item.address.to_raw())
            return self._update(nft_item, nft)
        except NoResultFound:
            logger.info(
                f"No NFT Item for address {nft_item.address!r} found. Creating new NFT Item."
            )
            return self._create(nft_item)

    def get(self, address: str) -> NftItem:
        return self.db_session.query(NftItem).filter(NftItem.address == address).one()

    def get_all(
        self, owner_address: str | None = None, collection_address: str | None = None
    ) -> list[NftItem]:
        query = self.db_session.query(NftItem)
        if owner_address:
            query = query.filter(NftItem.owner_address == owner_address)

        if collection_address:
            query = query.filter(NftItem.collection_address == collection_address)
        return query.all()

    def bulk_create_or_update(
        self, nft_items: NftItems, whitelist_collection_addresses: list[str]
    ) -> list[NftItem]:
        created_or_updated_nfts = []
        for nft_item in nft_items.nft_items:
            if (
                not nft_item.collection
                or nft_item.collection.address.to_raw()
                not in whitelist_collection_addresses
            ):
                continue

            created_or_updated_nfts.append(self.create_or_update(nft_item))
        self.db_session.commit()
        return created_or_updated_nfts

    def count(self) -> int:
        return self.db_session.query(NftItem).count()
