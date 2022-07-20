from typing import AnyStr, Dict

from marshmallow import Schema, fields
from she_logging import logger

from dhos_async_adapter.clients import bg_readings_api
from dhos_async_adapter.helpers.validation import validate_message_body_dict

ROUTING_KEY = "gdm.166922008"


class AbnormalBgReadingMessage(Schema):
    uuid = fields.String(required=True, description="BG Reading UUID")


def process(body: AnyStr) -> None:
    """
    - Summary: Triggers processing of an abnormal blood glucose reading in the BG Readings API service.
    - Routing Key: gdm.166922008
    - Body: Details of a blood glucose reading that was flagged as abnormal.
    - Notes: This mechanism is how GDM "counts" alerts are generated.
    - Endpoint(s): POST /gdm-bg-readings/gdm/v1/process_alerts/reading/<reading_uuid>
    """
    logger.info("Received 'abnormal BG reading' message (%s)", ROUTING_KEY)

    # Load and validate message body.
    logger.debug(
        "Abnormal reading message body (%s)",
        ROUTING_KEY,
        extra={"message_body": body},
    )
    reading: Dict = validate_message_body_dict(body, AbnormalBgReadingMessage)

    # Post message to BG Readings API.
    bg_readings_api.create_reading(reading)
