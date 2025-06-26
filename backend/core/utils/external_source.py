import logging
import ssl

import httpx
from pydantic import ValidationError

from core.constants import REQUEST_TIMEOUT, READ_TIMEOUT, CONNECT_TIMEOUT
from core.dtos.chat.rule.whitelist import WhitelistRuleCPO
from core.exceptions.chat import TelegramChatInvalidExternalSourceError


logger = logging.getLogger(__name__)

# Create the default SSL context and ensure it validates both the certificate and the hostname
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED

timeout = httpx.Timeout(REQUEST_TIMEOUT, read=READ_TIMEOUT, connect=CONNECT_TIMEOUT)


async def fetch_dynamic_allowed_members(
    url: str,
    auth_key: str | None = None,
    auth_value: str | None = None,
) -> WhitelistRuleCPO:
    """
    Fetches a dynamic list of allowed members from an external source using the provided URL
    and optional authentication credentials. It makes an asynchronous HTTP GET request, validates
    the response against a model, and returns the validated data.

    :param url: The URL of the external source to fetch the allowed members from.
    :param auth_key: Optional key to be used for authorization in the HTTP headers.
    :param auth_value: Optional value corresponding to the authorization key for HTTP headers.
    :return: A validated instance of WhitelistRuleCPO containing the fetched allowed members.
    :raises HTTPStatusError: If the HTTP request fails or returns a non-2xx status code.
    :raises TelegramChatInvalidExternalSourceError: If the response fails validation.
    """
    headers = {}
    if auth_key and auth_value:
        headers = {auth_key: auth_value}

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True, verify=ssl_context
    ) as client:
        response = await client.get(url, headers=headers)
    response.raise_for_status()
    try:
        validated_response = WhitelistRuleCPO.model_validate(
            response.json(), strict=True
        )
    except ValidationError as e:
        raise TelegramChatInvalidExternalSourceError(str(e))

    logger.info(f"Fetched {len(validated_response.users)} from {url}.")
    return validated_response
