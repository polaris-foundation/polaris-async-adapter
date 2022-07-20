from typing import AnyStr, Dict, List, Optional, Tuple

from she_logging import logger

from dhos_async_adapter.clients import connector_api, encounters_api, observations_api
from dhos_async_adapter.helpers import actions
from dhos_async_adapter.helpers.actions import ActionsMessage
from dhos_async_adapter.helpers.exceptions import RejectMessageError
from dhos_async_adapter.helpers.timestamps import generate_iso8601_timestamp
from dhos_async_adapter.helpers.validation import validate_message_body_dict

ROUTING_KEY = "dhos.DM000002"


def process(body: AnyStr) -> None:
    """
    - Summary: Checks for orphaned observations sets in Observations API and merges them if required.
    - Routing Key: dhos.DM000002
    - Body: A group of actions in the format published by the Connector API service.
    - Notes: Merges encounter in Encounters API if required, then updates message in Connector API.
    - Endpoint(s):
      - GET /dhos-observations/dhos/v2/observation_set
      - GET /dhos-encounters/dhos/v1/encounter/<encounter_uuid>
      - POST /dhos-encounters/dhos/v2/encounter
      - PATCH /dhos-encounters/dhos/v1/encounter/<encounter_uuid>
      - PATCH /dhos-connector/dhos/v1/message/<message_uuid>

    Orphaned observation sets can occur if an encounter is marked as cancelled (deleted). In order to retain
    visibility of any observation sets taken against the deleted encounter, a new discharged local encounter
    must be created and the original cancelled encounter made a child of this new encounter. This then allows
    for the local encounter to be merged into the next known EPR encounter.
    """
    logger.info(
        "Received check orphaned observations message (%s)",
        ROUTING_KEY,
    )

    # Load and validate message body.
    logger.debug(
        "Check orphaned observations message body (%s)",
        ROUTING_KEY,
        extra={"message_body": body},
    )
    orphaned_obs_message: Dict = validate_message_body_dict(
        body=body, schema=ActionsMessage
    )

    internal_message_id: str = orphaned_obs_message["dhos_connector_message_uuid"]
    encounter_uuid, patient_uuid = _extract_uuids(orphaned_obs_message)

    # Get observation sets from Observations API.
    observation_sets: List[Dict] = observations_api.get_observation_sets(
        encounter_uuid=encounter_uuid
    )

    # If the deleted encounter has observation sets, we need to merge it into a new local encounter.
    logger.debug(
        "Retrieved %d observation sets for encounter %s (%s)",
        len(observation_sets),
        encounter_uuid,
        ROUTING_KEY,
    )
    if len(observation_sets) > 0:
        encounter_to_merge: Dict = encounters_api.get_encounter_by_uuid(
            encounter_uuid=encounter_uuid, show_deleted=True
        )
        if encounter_to_merge.get("child_of"):
            # Encounter has already been merged.
            logger.warning(
                "Aborting merge, encounter '%s' is already a child of '%s' (%s)",
                encounter_to_merge["uuid"],
                encounter_to_merge["child_of"],
                ROUTING_KEY,
            )
        else:
            _merge_into_local_encounter(
                encounter_to_merge=encounter_to_merge, patient_uuid=patient_uuid
            )

    logger.debug("Marking HL7 message as fully processed (%s)", ROUTING_KEY)
    connector_api.patch_hl7_message(
        message_uuid=internal_message_id,
        message_body={"is_processed": True},
    )


def _extract_uuids(message: Dict) -> Tuple[str, str]:
    """
    Extracts the encounter UUID from the correct action.
    """
    encounter_data: Dict = actions.extract_action(
        message=message,
        action_name="check_for_orphaned_observations",
    )["data"]
    encounter_uuid: Optional[str] = encounter_data.get("encounter_uuid")
    patient_uuid: Optional[str] = encounter_data.get("patient_uuid")

    if not (
        encounter_uuid
        and patient_uuid
        and isinstance(encounter_uuid, str)
        and isinstance(patient_uuid, str)
    ):
        logger.exception("Failed to validate check orphaned observations data")
        raise RejectMessageError()

    return encounter_uuid, patient_uuid


def _merge_into_local_encounter(encounter_to_merge: Dict, patient_uuid: str) -> None:
    # Create discharged local encounter, and merge the original encounter into it.
    encounter_details: Dict = {
        "location_uuid": encounter_to_merge["location_uuid"],
        "dh_product_uuid": encounter_to_merge["dh_product"][0]["uuid"],
        "patient_record_uuid": encounter_to_merge["patient_record_uuid"],
        "patient_uuid": patient_uuid,
        "encounter_type": encounter_to_merge["encounter_type"],
        "admitted_at": encounter_to_merge["admitted_at"],
        "score_system": encounter_to_merge["score_system"],
        "spo2_scale": encounter_to_merge.get("spo2_scale"),
        "discharged_at": generate_iso8601_timestamp(),
    }
    parent_encounter = encounters_api.create_encounter(encounter_details)
    encounters_api.update_encounter_by_uuid(
        encounter_uuid=encounter_to_merge["uuid"],
        encounter_data={"child_of_encounter_uuid": parent_encounter["uuid"]},
    )
