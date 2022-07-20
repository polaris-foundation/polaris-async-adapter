from typing import AnyStr, Dict

from she_logging import logger

from dhos_async_adapter.clients import activation_auth_api
from dhos_async_adapter.helpers.activation_auth_clinician import ActivationAuthClinician
from dhos_async_adapter.helpers.validation import validate_message_body_dict

ROUTING_KEY = "dhos.D9000001"


def process(body: AnyStr) -> None:
    """
    - Summary: Creates a clinician in Activation Auth API.
    - Routing Key: dhos.D9000001
    - Body: A clinician's details.
    - Notes: Used for creating SEND Entry login credentials.
    - Endpoint(s): POST /dhos-activation-auth/dhos/v1/clinician
    """
    logger.info("Received 'create clinician' message (%s)", ROUTING_KEY)

    # Load and validate message body.
    logger.debug(
        "Create clinician message body (%s)",
        ROUTING_KEY,
        extra={"message_body": body},
    )
    clinician_details: Dict = validate_message_body_dict(
        body=body, schema=ActivationAuthClinician
    )
    clinician_details["clinician_id"] = clinician_details.pop("uuid")
    clinician_details["products"] = [
        p["product_name"] for p in clinician_details.pop("products")
    ]

    # Post clinician to Activation Auth API.
    activation_auth_api.create_clinician(clinician_details=clinician_details)
