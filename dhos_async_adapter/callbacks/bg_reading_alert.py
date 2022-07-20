from enum import Enum
from typing import AnyStr, Dict, Optional, Tuple

from marshmallow import Schema, fields, validate
from she_logging import logger

from dhos_async_adapter.clients import messages_api, services_api
from dhos_async_adapter.helpers.exceptions import RejectMessageError
from dhos_async_adapter.helpers.validation import validate_message_body_dict

ROUTING_KEY = "gdm.424167000"


class AlertType(Enum):
    COUNTS_RED = "COUNTS_RED"
    COUNTS_AMBER = "COUNTS_AMBER"
    PERCENTAGES_RED = "PERCENTAGES_RED"
    PERCENTAGES_AMBER = "PERCENTAGES_AMBER"
    ACTIVITY_GREY = "ACTIVITY_GREY"


class BgReadingAlertMessage(Schema):

    patient_uuid = fields.String(required=True, description="Patient UUID")
    alert_type = fields.String(
        required=True,
        description="The alert type and system",
        validate=validate.OneOf([t.value for t in AlertType]),
    )


def process(body: AnyStr) -> None:
    """
    - Summary: Sends BG readings alert messages using the Messages API.
    - Routing Key: gdm.424167000
    - Body: An object containing a patient UUID and alert type
    - Notes: Sends an alert message to each location the patient belongs to. Aborts if patient is not a GDM patient.
    - Endpoint(s):
      - GET /dhos-services/dhos/v1/patient
      - POST /dhos-messages/dhos/v1/message
    """
    logger.info("Received 'BG reading alert' message (%s)", ROUTING_KEY)

    # Load and validate message body.
    logger.debug(
        "BG reading alert message body (%s)",
        ROUTING_KEY,
        extra={"message_body": body},
    )
    alert_message: Dict = validate_message_body_dict(body, BgReadingAlertMessage)
    patient_uuid: str = alert_message["patient_uuid"]
    alert_type: AlertType = AlertType(alert_message["alert_type"])

    if alert_type == AlertType.ACTIVITY_GREY:
        # We don't send alert messages for activity alerts.
        logger.info("No alert message to generate for patient %s", patient_uuid)
        return

    patient_details: Optional[Dict] = services_api.get_patient(
        patient_uuid=patient_uuid, product_name="GDM"
    )
    if patient_details is None:
        logger.info(
            "Patient %s is not a GDM patient, aborting BG reading alert", patient_uuid
        )
        return

    (alert_type_value, msg_body) = _extract_alert_message_details(
        alert_type=alert_type, first_name=patient_details["first_name"]
    )

    # Create a message in Messages API for each of the patient's locations.
    for location in patient_details["locations"]:
        logger.info("Creating alert message for location %s", location)
        message_details: Dict = {
            "sender": patient_uuid,
            "sender_type": "patient",
            "receiver": location,
            "receiver_type": "location",
            "message_type": {"value": alert_type_value},
            "content": msg_body,
        }
        # Post message to Messages API.
        messages_api.create_message(message_details)


def _extract_alert_message_details(
    alert_type: AlertType, first_name: str
) -> Tuple[int, str]:
    """
    Constructs alert message value (integer) and text for a given alert type.
    7 is the enum value for red alert message in Messages API.
    8 is the enum value for amber alert message in Messages API.
    """
    if alert_type == AlertType.COUNTS_RED:
        return (
            7,
            f"{first_name} has posted at least 3 consecutive out of threshold readings for this meal time.",
        )
    elif alert_type == AlertType.COUNTS_AMBER:
        return (
            8,
            f"{first_name} has posted at least 2 out of threshold readings"
            f" within the past 2 days where readings were taken",
        )
    elif alert_type == AlertType.PERCENTAGES_RED:
        return (
            7,
            f"At least 30% of readings posted by {first_name} in the last 7 days have been out of threshold.",
        )
    elif alert_type == AlertType.PERCENTAGES_AMBER:
        return (
            8,
            f"Between 10% and 30% of readings posted by {first_name} in the last 7 days have been out of threshold.",
        )
    # Can't get here due to previous validation.
    logger.error("Unknown alert type")
    raise RejectMessageError()
