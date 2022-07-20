from typing import Dict

from she_logging import logger

from dhos_async_adapter import config
from dhos_async_adapter.clients import do_request


def post_send_pdf(message_body: Dict) -> None:
    url = f"{config.DHOS_PDF_API_URL}/dhos/v1/send_pdf"
    logger.debug(
        "Posting SEND PDF message data to dhos-pdf-api",
        extra={"message_body": message_body},
    )
    do_request(url=url, method="post", payload=message_body)


def post_ward_pdf(message_body: Dict) -> None:
    url = f"{config.DHOS_PDF_API_URL}/dhos/v1/ward_report"
    logger.debug(
        "Posting Ward PDF message data to dhos-pdf-api",
        extra={"message_body": message_body},
    )
    do_request(url=url, method="post", payload=message_body)
