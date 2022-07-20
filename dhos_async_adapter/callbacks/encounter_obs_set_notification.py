from typing import AnyStr, Dict

import kombu_batteries_included
from marshmallow import INCLUDE, Schema, fields
from she_logging import logger

from dhos_async_adapter.clients import encounters_api
from dhos_async_adapter.helpers import actions
from dhos_async_adapter.helpers.actions import ActionsMessageNoConnectorId
from dhos_async_adapter.helpers.validation import validate_message_body_dict

ROUTING_KEY = "dhos.DM000004"


class ObservationSet(Schema):
    class Meta:
        unknown = INCLUDE

    encounter_id = fields.String(required=True)


class ProcessObservationSetAction(Schema):
    observation_set = fields.Nested(ObservationSet, required=True)


def process(body: AnyStr) -> None:
    """
    - Summary: Appends encounter information from Encounters API to a published observation set notification.
    - Routing Key: dhos.DM000004
    - Body: A group of actions in the format published by the Connector API service.
    - Notes: Part of the chain that results in an ORU HL7 message. Results in an dhos.DM000005 message being published.
    - Endpoint(s):
        - GET /dhos-encounters/dhos/v1/encounter/<encounter_uuid>
        - POST /dhos-encounters/dhos/v2/encounter
        - PATCH /dhos-encounters/dhos/v1/encounter/<encounter_uuid>
    """
    logger.info(
        "Received observation set notification message (%s)",
        ROUTING_KEY,
    )

    # Load and validate message body.
    logger.debug(
        "Observation set notification message body (%s)",
        ROUTING_KEY,
        extra={"message_body": body},
    )
    actions_message: Dict = validate_message_body_dict(
        body=body, schema=ActionsMessageNoConnectorId, unknown=INCLUDE
    )

    action_data = actions.extract_action(
        message=actions_message, action_name="process_observation_set"
    )["data"]

    validated_action_data: Dict = ProcessObservationSetAction().load(
        action_data, unknown=INCLUDE
    )

    # Get the encounter details
    encounter: Dict = encounters_api.get_encounter_by_uuid(
        encounter_uuid=validated_action_data["observation_set"]["encounter_id"]
    )
    validated_action_data["encounter"] = encounter

    processed_msg = {
        "actions": [{"name": "process_observation_set", "data": validated_action_data}]
    }
    kombu_batteries_included.publish_message(
        routing_key="dhos.DM000005", body=processed_msg
    )
