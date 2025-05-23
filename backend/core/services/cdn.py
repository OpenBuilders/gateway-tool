from collections.abc import Callable
from pathlib import Path

import aioboto3

from core.settings import core_settings


class CDNService:
    def __init__(self):
        self.session = aioboto3.Session(
            aws_access_key_id=core_settings.cdn_access_key,
            aws_secret_access_key=core_settings.cdn_secret_key,
            region_name=core_settings.cdn_region,
        )

    async def upload_file(
        self,
        file_path: Path | str,
        object_name: str,
        callback: Callable[[None], None] | None = None,
    ) -> None:
        async with self.session.client(
            "s3",
            endpoint_url=core_settings.cdn_endpoint,
        ) as client:
            await client.upload_file(
                Filename=file_path,
                Bucket=core_settings.cdn_bucket_name,
                Key=object_name,
                Callback=callback,
            )
