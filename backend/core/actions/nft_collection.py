import asyncio
import logging
from tempfile import NamedTemporaryFile

from fastapi import HTTPException
from pytonapi.schema.nft import NftCollection
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from core.dtos.resource import NftCollectionDTO
from core.actions.base import BaseAction
from core.constants import DEFAULT_EXPIRY_TIMEOUT_MINUTES
from core.services.cdn import CDNService
from core.services.nft import NftCollectionService
from core.services.superredis import RedisService
from core.utils.file import pick_best_preview, download_media
from indexer.indexers.tonapi import TonApiService

logger = logging.getLogger(__name__)


class NftCollectionAction(BaseAction):
    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)
        self.nft_collection_service = NftCollectionService(db_session)
        self.cdn_service = CDNService()
        self.blockchain_service = TonApiService()
        self.cdn_service = CDNService()
        self.redis_service = RedisService()

    async def prefetch(self, address_raw: str) -> NftCollectionDTO:
        try:
            nft_collection = self.nft_collection_service.get(address_raw)
            logger.info(
                f"NFT collection {address_raw!r} already exists in the database."
            )
            return NftCollectionDTO.from_orm(nft_collection)
        except NoResultFound:
            logger.info(
                f"NFT collection {address_raw!r} not found in the database. Prefetching..."
            )
            dto = await self.get_cached_blockchain_info(address_raw)
            return dto

    @staticmethod
    def _get_resource_cache_key(address_raw: str) -> str:
        return f"nft-collection:{address_raw}"

    async def get_cached_blockchain_info(self, address_raw: str) -> NftCollectionDTO:
        """
        Fetches and caches blockchain information for a given address.

        This asynchronous method retrieves NFT collection data by first checking the
        cache for a corresponding entry. If cached data is found, it is used directly;
        otherwise, the data is fetched from a blockchain API. Upon successfully
        retrieving blockchain data, this method caches the result for future use and
        returns the corresponding NFT collection data transfer object (DTO).

        :param address_raw: The raw address string for which to fetch blockchain
            information.
        :return: An instance of NftCollectionDTO containing information related to
            the NFT collection associated with the given address.
        """
        cached_value = self.redis_service.get(self._get_resource_cache_key(address_raw))
        if cached_value:
            logger.info("Using cached nft collection info for %s", address_raw)
            dto = NftCollectionDTO.model_validate_json(cached_value)
        else:
            logger.info("Fetching nft collection info for %s from the API", address_raw)
            jetton_info, logo_path = await self._get_blockchain_info(
                address_raw=address_raw
            )
            dto = NftCollectionDTO.from_info(jetton_info, logo_path)
            logger.info("Caching nft collection info for %s", address_raw)
            self.redis_service.set(
                self._get_resource_cache_key(address_raw),
                dto.model_dump_json(),
                ex=DEFAULT_EXPIRY_TIMEOUT_MINUTES * 60,
            )
        return dto

    async def _get_blockchain_info(
        self, address_raw: str
    ) -> tuple[NftCollection, str | None]:
        """
        Fetches blockchain information for a given address, including NFT collection details
        and optionally a download URL for a logo if available.
        If URL is available, it tries to download the logo and upload it to CDN.

        :param address_raw: The raw address string to retrieve blockchain data for.
        :return: A tuple containing the NFT collection data and an optional path to the logo file.
        """
        nft_collection_data = await self.blockchain_service.get_nft_collection_info(
            address_raw
        )
        logo_path = None
        if nft_collection_data.previews:
            best_preview = pick_best_preview(nft_collection_data.previews)
            download_url = best_preview.url
            with NamedTemporaryFile(mode="w+b", delete=True) as tmp_file:
                file_extension = download_media(download_url, tmp_file)
                if file_extension:
                    logo_path = f"{address_raw}.{file_extension}"
                    await self.cdn_service.upload_file(
                        file_path=tmp_file.name, object_name=logo_path
                    )

        return nft_collection_data, logo_path

    def get_all(self, whitelisted_only: bool) -> list[NftCollectionDTO]:
        nft_collections = self.nft_collection_service.get_all(
            whitelisted_only=whitelisted_only
        )
        return [
            NftCollectionDTO.from_orm(nft_collection)
            for nft_collection in nft_collections
        ]

    def get(self, address_raw: str) -> NftCollectionDTO:
        nft_collection = self.nft_collection_service.get(address_raw)
        return NftCollectionDTO.from_orm(nft_collection)

    async def create(self, address_raw: str) -> NftCollectionDTO:
        """
        Creates a new NFT collection based on the provided blockchain address.

        This asynchronous method retrieves cached blockchain information for the
        given address, parses the metadata using the blockchain service, and
        creates a new NFT collection. The resulting DTO is constructed and
        returned as part of the operation.

        :param address_raw: The raw blockchain address used for retrieving and
            creating the NFT collection.
        :return: An instance of NftCollectionDTO containing the created NFT
            collection's data.
        """
        dto = await self.get_cached_blockchain_info(address_raw)
        blockchain_metadata = (
            await self.blockchain_service.parse_nft_collection_metadata(address_raw)
        )
        dto.blockchain_metadata = blockchain_metadata
        nft_collection = self.nft_collection_service.create(dto=dto)
        return NftCollectionDTO.from_orm(nft_collection)

    async def get_or_create(self, address_raw: str) -> NftCollectionDTO:
        """
        Retrieve an existing NFT collection or create a new one based on the provided address.

        This method attempts to find an existing NFT collection corresponding to the given address.
        If no such collection exists, it creates a new one. Logging is performed when a new collection
        needs to be created.

        :param address_raw: The raw address used to retrieve or create the NFT collection.
        :return: An NFT collection data transfer object (DTO) corresponding to the given address.
        """
        try:
            return self.get(address_raw)
        except NoResultFound:
            logger.info(
                f"No nft collection item found for {address_raw}. Creating new one."
            )
            return await self.create(address_raw)

    async def _refresh_metadata(self, task_id: str, address_raw: str) -> None:
        """
        Refresh the metadata of a Non-Fungible Token (NFT) collection by retrieving
        data from the blockchain service, updating it within the local metadata
        service, and removing the task status from Redis once the operation is
        completed.

        :param task_id: Unique identifier associated with the task in Redis.
        :param address_raw: The raw address of the NFT collection to refresh metadata for.
        :return: This function does not return anything.
        """
        blockchain_metadata = (
            await self.blockchain_service.parse_nft_collection_metadata(
                address_raw, partial=False
            )
        )
        self.nft_collection_service.update_metadata(
            address=address_raw, blockchain_metadata=blockchain_metadata
        )
        self.redis_service.pop_task_status(task_id)

    async def refresh_metadata(self, address_raw: str) -> None:
        """
        Refresh metadata associated with the specified address. This method triggers an
        asynchronous task to perform the metadata refresh operation. If a task with the
        same address is already in progress, it raises an HTTP exception with conflict
        status.

        :param address_raw: Raw address as a string. Used to identify the task and
            refresh the specific metadata.
        :return: None if the task is successfully initiated or an exception is raised
            if a task is already in progress for the same address.
        """
        task_id = f"refresh_metadata_{address_raw}"
        if task_status := self.redis_service.check_task_status(task_id):
            # redis_service.pop_task_status(task_id)
            raise HTTPException(
                status_code=409,
                detail=f"Task is already in progress. Status: {task_status}",
            )
        self.redis_service.set_task_status(task_id, "in_progress")

        asyncio.create_task(self._refresh_metadata(task_id, address_raw))

    async def update(self, address_raw: str, is_enabled: bool) -> NftCollectionDTO:
        """
        Updates the status of an NFT collection based on the provided address
        and status flag. This method interacts with the NFT collection service
        to perform the update and returns a data transfer object (DTO) created
        from the updated collection.

        :param address_raw: The address of the NFT collection to be updated.
        :param is_enabled: The status flag indicating whether the NFT
            collection should be enabled or disabled.
        :return: A DTO representing the updated NFT collection.
        """
        nft_collection = self.nft_collection_service.update_status(
            address_raw, is_enabled
        )
        return NftCollectionDTO.from_orm(nft_collection)
