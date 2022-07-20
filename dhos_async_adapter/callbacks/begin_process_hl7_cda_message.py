from typing import AnyStr, Dict

from she_logging import logger

from dhos_async_adapter.clients import connector_api
from dhos_async_adapter.helpers.actions import HL7CDAMessage
from dhos_async_adapter.helpers.validation import validate_message_body_dict

ROUTING_KEY = "dhos.423779001"


def process(body: AnyStr) -> None:
    """
    - Summary: Begin processing HL7 CDA message using the Connector API.
    - Routing Key: dhos.423779001
    - Body: Message details.
    - Notes: Used for async ACK.
    - Endpoint(s): POST /dhos-connector/dhos/v1/cda_message
    """

    logger.info("Processing HL7 CDA message")

    message_body: Dict = validate_message_body_dict(body=body, schema=HL7CDAMessage)

    connector_api.post_cda_message(
        message_body={"type": "HL7v3CDA", "content": message_body["content"]},
    )
