from typing import Dict

import requests
from she_logging import logger

from dhos_async_adapter import config
from dhos_async_adapter.clients import do_request


def create_message(message_details: Dict) -> None:
    url = f"{config.DHOS_MESSAGES_API_URL}/dhos/v2/message"
    logger.debug(
        "Posting message to dhos-messages-api", extra={"message_body": message_details}
    )
    response: requests.Response = do_request(
        url=url, method="post", payload=message_details
    )
    logger.debug(
        "Message for sender '%s' POSTed successfully, HTTP status %d",
        message_details["sender"],
        response.status_code,
    )
