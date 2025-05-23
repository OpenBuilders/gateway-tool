import logging

from httpx import AsyncClient, Timeout

from core.constants import REQUEST_TIMEOUT, READ_TIMEOUT, CONNECT_TIMEOUT
from core.dtos.sticker import (
    ExternalStickerDomCollectionOwnershipDTO,
    StickerDomCollectionOwnershipMetadataDTO,
    StickerDomCollectionWithCharacters,
)
from core.utils.cipher import load_private_key, rsa_decrypt_wrapped_dek, aes_decrypt
from indexer.settings import indexer_settings

timeout = Timeout(REQUEST_TIMEOUT, read=READ_TIMEOUT, connect=CONNECT_TIMEOUT)

DEFAULT_NONCE_SIZE = 12
DEFAULT_TAG_SIZE = 16

logger = logging.getLogger(__name__)


class StickerDomService:
    def __init__(self) -> None:
        self.private_key = load_private_key(
            indexer_settings.sticker_dom_private_key_path
        )

    @staticmethod
    def _get_ownership_url(collection_id: int) -> str:
        return (
            f"{indexer_settings.sticker_dom_base_url}/data/ownership"
            f"?consumer_id={indexer_settings.sticker_dom_consumer_id}"
            f"&collection_id={collection_id}"
        )

    @staticmethod
    def _get_collections_url() -> str:
        return f"{indexer_settings.sticker_dom_data_storage_base_url}/collections.json"

    async def fetch_collections(self):
        async with AsyncClient() as client:
            response = await client.get(self._get_collections_url())
            response.raise_for_status()
            collections = response.json()

        return [
            StickerDomCollectionWithCharacters.from_json(collection)
            for collection in collections
        ]

    async def fetch_collection_ownership_metadata(
        self,
        collection_id: int,
    ) -> StickerDomCollectionOwnershipMetadataDTO | None:
        """
        Fetches metadata associated with collection ownership by interacting with an external
        API and returns a DTO containing relevant details. It involves retrieving metadata
        from a specified endpoint, extracting and decrypting the wrapped DEK (Data Encryption
        Key), and packaging the data into a structured DTO format. Returns None if the
        metadata retrieval fails.

        :param collection_id: An integer representing the unique identifier of the collection
            whose ownership metadata is to be fetched.
        :return: A DTO object (`StickerDomCollectionOwnershipMetadataDTO`) containing metadata
            about the collection ownership, or None if the operation fails.
        """
        async with AsyncClient() as client:
            # Step 1: Get URL for collection data bucket with wrapped DEK
            headers = {}
            if indexer_settings.sticker_dom_ownership_header_key:
                headers[
                    indexer_settings.sticker_dom_ownership_header_key
                ] = indexer_settings.sticker_dom_ownership_header_value
            meta_response = await client.get(
                self._get_ownership_url(collection_id),
                headers=headers,
            )
            meta_response.raise_for_status()

            metadata = meta_response.json()
            if not metadata["ok"]:
                logger.error(
                    f"Can't get metadata for collection {collection_id!r}: {metadata['errorCode']}"
                )
                return None

            # Step 2: Extract URL and DEK from the response metadata
            bucket_url = metadata["data"]["url"]
            wrapped_dek = metadata["data"]["key"]

            # Step 3: Decode wrapped DEK with a private key
            plain_dek = rsa_decrypt_wrapped_dek(
                wrapped_dek=bytes.fromhex(wrapped_dek), private_key=self.private_key
            )
            return StickerDomCollectionOwnershipMetadataDTO(
                collection_id=collection_id,
                url=bucket_url,
                plain_dek_hex=plain_dek.hex(),
            )

    @staticmethod
    async def fetch_collection_ownership_data(
        metadata: StickerDomCollectionOwnershipMetadataDTO,
    ) -> ExternalStickerDomCollectionOwnershipDTO:
        """
        Fetch the collection ownership data asynchronously for a given metadata.

        This function performs an encrypted data fetch operation using HTTP GET
        request and decrypts the received bucket data with AES-GCM encryption.
        It processes the decrypted raw data into a structured DTO object for
        further use.

        :param metadata: Object containing metadata needed to fetch and decrypt
                         the collection ownership data.
        :return: Structured data transfer object (DTO) containing decrypted
                 and parsed ownership data.
        :raises HTTPError: If the request to the metadata URL fails.
        :raises ValueError: If decryption of the data fails due to an invalid
                            nonce, ciphertext, or tag.
        """
        async with AsyncClient() as client:
            # Step 4: Get encrypted bucket data
            response = await client.get(url=metadata.url)
            response.raise_for_status()
            # Step 5: Split response content for nonce, ciphertext, and tag
            nonce, ciphertext, tag = (
                response.content[:DEFAULT_NONCE_SIZE],
                response.content[DEFAULT_NONCE_SIZE:-DEFAULT_TAG_SIZE],
                response.content[-DEFAULT_TAG_SIZE:],
            )
            # Step 6: Decrypt bucket data with AES-GCM
            raw_collections_data = aes_decrypt(
                nonce,
                ciphertext,
                dek=metadata.plain_dek,
                tag=tag,
            )
            return ExternalStickerDomCollectionOwnershipDTO.from_raw(
                raw_collections_data,
                collection_id=metadata.collection_id,
            )
