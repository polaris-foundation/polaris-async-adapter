from typing import AnyStr, Dict, Optional

from marshmallow import INCLUDE, Schema, ValidationError, fields
from she_logging import logger

from dhos_async_adapter.clients import (
    connector_api,
    locations_api,
    services_api,
    users_api,
)
from dhos_async_adapter.helpers import actions
from dhos_async_adapter.helpers.actions import (
    ActionsMessageNoConnectorId,
    ProcessObservationSetData,
)
from dhos_async_adapter.helpers.exceptions import RejectMessageError
from dhos_async_adapter.helpers.validation import validate_message_body_dict

ROUTING_KEY = "dhos.DM000005"


class ObservationSet(Schema):
    class Meta:
        unknown = INCLUDE

    created_by = fields.String(required=True)


class Encounter(Schema):
    class Meta:
        unknown = INCLUDE

    patient_record_uuid = fields.String(required=True)
    location_uuid = fields.String(required=True)


class ProcessObservationSetAction(Schema):
    observation_set = fields.Nested(ObservationSet, required=True)
    encounter = fields.Nested(Encounter, required=True)


def process(body: AnyStr) -> None:
    """
    - Summary: Creates an ORU message in Connector API.
    - Routing Key: dhos.DM000005
    - Body: A group of actions in the format published by the Connector API service.
    - Notes: Appends patient data to existing encounter/observation data and triggers sending of an ORU message.
    - Endpoint(s):
        - GET /dhos-services/dhos/v1/patient/record/<record_uuid>
        - GET /dhos-users/dhos/v1/clinician/<clinician_uuid>
        - GET /dhos-locations/dhos/v1/location/<location_uuid>
        - POST /dhos-connector/dhos/v1/oru_message
    """
    logger.info(
        "Received services observation set notification message (%s)",
        ROUTING_KEY,
    )

    # Load and validate message body.
    logger.debug(
        "Services observation set notification message body (%s)",
        ROUTING_KEY,
        extra={"message_body": body},
    )
    actions_message: Dict = validate_message_body_dict(
        body=body, schema=ActionsMessageNoConnectorId, unknown=INCLUDE
    )

    process_obs_set_action = actions.extract_action(
        message=actions_message, action_name="process_observation_set"
    )
    try:
        action_data: Dict = ProcessObservationSetAction().load(
            process_obs_set_action["data"], unknown=INCLUDE
        )
    except ValidationError:
        logger.exception("Failed to validate observation set action")
        raise RejectMessageError()

    # Append patient details.
    record_uuid: str = action_data["encounter"]["patient_record_uuid"]
    logger.debug("Getting patient details for record UUID %s", record_uuid)
    patient: Dict = services_api.get_patient_by_record_id(
        record_uuid=record_uuid, compact=True
    )
    action_data["patient"] = patient

    # Maybe append clinician details.
    clinician_uuid: str = action_data["observation_set"]["created_by"]
    logger.debug("Getting clinician details for UUID %s", clinician_uuid)
    clinician: Optional[Dict] = users_api.get_clinician_by_uuid(clinician_uuid)
    if clinician is not None:
        action_data["clinician"] = clinician

    # Append location ODS code.
    location_uuid: str = action_data["encounter"]["location_uuid"]
    logger.debug("Getting location details for UUID %s", location_uuid)
    location: Dict = locations_api.get_location_by_uuid(location_uuid)
    action_data["encounter"]["location_ods_code"] = location.get("ods_code")

    # Validate data for ORU message POST.
    try:
        ProcessObservationSetData().load(action_data)
    except ValidationError:
        logger.exception("Failed to validate observation set action")
        raise RejectMessageError()

    oru_message_details = {
        "actions": [{"name": "process_observation_set", "data": action_data}]
    }
    connector_api.post_oru_message(message_body=oru_message_details)
