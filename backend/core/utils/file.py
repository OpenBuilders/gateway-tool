import logging
import re
from pathlib import Path
from typing import IO

from httpx import Client, Response
from pytonapi.schema.nft import ImagePreview


client = Client()

logger = logging.getLogger(__name__)


CONTENT_DISPOSITION_FILENAME_REGEX = re.compile(r'filename="(.+)"')


def get_filename_from_content_disposition(response: Response) -> str | None:
    """
    Extract filename from Content-Disposition header.
    """
    content_disposition = response.headers.get("Content-Disposition")
    match = CONTENT_DISPOSITION_FILENAME_REGEX.search(content_disposition)
    if match:
        return match.group(1)
    return None


def guess_file_extension(response: Response) -> str | None:
    """
    Guess the file extension from the response content type.
    """
    content_type = response.headers.get("Content-Type")
    if content_type:
        return content_type.split("/")[-1]

    if filename := get_filename_from_content_disposition(response):
        return filename.split(".")[-1]

    return None


def download_media(
    url: str,
    target_location: IO[bytes],
    default_extension: str = "webp",
) -> str | None:
    """
    Downloads media from a URL and writes it to the specified location. If the file
    extension cannot be determined, a default extension is applied. The function
    also returns the appropriate file extension used for the media, or None in
    case of failure.

    :param url: The URL of the media file to be downloaded.
    :param target_location: A writable binary stream where the media content
        will be saved.
    :param default_extension: Optional default file extension to use if the
        file extension cannot be determined. The default is ".webp".
    :return: The file extension that is applied to the downloaded media or None if
        the download fails.
    """
    try:
        response = client.get(url)
    except:  # noqa: E722
        logger.exception("Unable to download media")
        return None

    file_extension = guess_file_extension(response) or default_extension
    target_location.write(response.content)
    return file_extension


def pick_best_preview(previews: list[ImagePreview]) -> ImagePreview:
    """
    Pick the best image preview from a list of previews.
    """
    try:
        return max(
            previews,
            key=lambda preview: preview.resolution.split("x")[0]
            * preview.resolution.split("x")[1],
        )
    except (TypeError, ValueError):
        logger.warning("Could not pick the best preview. Returning the last one")
        return previews[-1]


def clean_old_versions(
    path: Path,
    prefix: str,
    current_file: str,
) -> None:
    """
    Clean old versions of files in a path

    :param path: Path to the directory containing the files.
    :param prefix: Prefix of the files to clean.
    :param current_file: Current file name.
    """
    for file in path.glob(f"{prefix}*"):
        if file.name != current_file:
            file.unlink()
