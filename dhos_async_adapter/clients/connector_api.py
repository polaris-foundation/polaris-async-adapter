from typing import Dict

from she_logging import logger

from dhos_async_adapter import config
from dhos_async_adapter.clients import do_request


def patch_hl7_message(message_uuid: str, message_body: Dict) -> None:
    url = f"{config.DHOS_CONNECTOR_API_URL}/dhos/v1/message/{message_uuid}"
    logger.debug(
        "Patching message to dhos-connector-api",
        extra={"message_body": message_body},
    )
    do_request(url=url, method="patch", payload=message_body)


def post_oru_message(message_body: Dict) -> None:
    url = f"{config.DHOS_CONNECTOR_API_URL}/dhos/v1/oru_message"
    logger.debug("Posting ORU message data to dhos-connector-api")
    do_request(url=url, method="post", payload=message_body)


def post_hl7_message(message_uuid: str, message_body: Dict) -> None:
    url = f"{config.DHOS_CONNECTOR_API_URL}/dhos/v1/message/{message_uuid}/process"
    logger.debug("Posting HL7 message for processing to dhos-connector-api")
    do_request(url=url, method="post", payload=message_body)


def post_cda_message(message_body: Dict) -> None:
    url = f"{config.DHOS_CONNECTOR_API_URL}/dhos/v1/cda_message"
    logger.debug("Posting HL7 CDA message for processing to dhos-connector-api")
    do_request(url=url, method="post", payload=message_body)
