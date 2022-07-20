from typing import Dict

from she_logging import logger

from dhos_async_adapter import config
from dhos_async_adapter.clients import do_request


def create_email(email_details: Dict) -> None:
    url = f"{config.DHOS_NOTIFICATIONS_API_URL}/dhos/v1/email"
    logger.debug(
        "Post message to dhos-notifications-api",
        extra={"message_body": email_details},
    )
    do_request(url=url, method="post", payload=email_details)
