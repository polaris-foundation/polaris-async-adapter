from typing import AnyStr, Dict, List, Optional

import kombu_batteries_included
from marshmallow import EXCLUDE, Schema, fields
from she_logging import logger

from dhos_async_adapter.callbacks import check_orphaned_observations
from dhos_async_adapter.clients import connector_api, encounters_api
from dhos_async_adapter.helpers import actions
from dhos_async_adapter.helpers.actions import ActionsMessage
from dhos_async_adapter.helpers.timestamps import generate_iso8601_timestamp
from dhos_async_adapter.helpers.validation import validate_message_body_dict

ROUTING_KEY = "dhos.305058001"


class EncounterUpdateMessage(Schema):
    patient_uuid = fields.String(required=True)
    location_uuid = fields.String(required=True)
    dh_product_uuid = fields.String(required=True)
    patient_record_uuid = fields.String(required=True)
    epr_encounter_id = fields.String(required=True)
    encounter_type = fields.String(required=True)
    admitted_at = fields.String(required=True)
    score_system = fields.String(required=False, allow_none=True)
    score_system_default_for_location = fields.String(required=True)
    spo2_scale = fields.Integer(required=False, allow_none=True)
    admission_cancelled = fields.Boolean(required=False, load_default=False)
    discharge_cancelled = fields.Boolean(required=False, load_default=False)
    discharged_at = fields.String(required=False, allow_none=True)
    patient_deceased = fields.Boolean(required=False, load_default=False)
    merge_patient_record_uuid = fields.String(required=False, allow_none=True)


def process(body: AnyStr) -> None:
    """
    - Summary: Processes an encounter update received via HL7 messages, and updates Encounters API as appropriate.
    - Routing Key: dhos.305058001
    - Body: A group of actions in the format published by the Connector API service.
    - Notes: Encounter updating logic is complex and may include creating, updating or merging various encounters.
    - Endpoint(s):
        - GET /dhos-encounters/dhos/v2/encounter
        - POST /dhos-encounters/dhos/v2/encounter
        - PATCH /dhos-encounters/dhos/v1/encounter/<encounter_uuid>
        - POST /dhos-encounters/dhos/v1/encounter/merge
        - PATCH /dhos-connector/dhos/v1/message/<message_uuid>
    """
    logger.info("Received process encounter message (%s)", ROUTING_KEY)

    # Load and validate message body.
    logger.debug(
        "Process encounter message body (%s)",
        ROUTING_KEY,
        extra={"message_body": body},
    )
    process_encounter_message: Dict = validate_message_body_dict(
        body=body, schema=ActionsMessage
    )

    # Extract the encounter data, and process it into the form required by Encounters API.
    connector_message_id: str = process_encounter_message["dhos_connector_message_uuid"]
    encounter_data: Dict = _extract_encounter_data(process_encounter_message)
    patient_uuid: str = encounter_data["patient_uuid"]
    patient_deceased: bool = encounter_data.pop("patient_deceased", False)
    merge_patient_record_uuid: Optional[str] = encounter_data.pop(
        "merge_patient_record_uuid", None
    )
    score_system_default_for_location: str = encounter_data.pop(
        "score_system_default_for_location"
    )
    open_local_encounters: List[Dict] = encounters_api.get_open_local_encounters(
        patient_uuid
    )
    epr_encounters: List[Dict] = encounters_api.get_epr_encounters(
        patient_uuid, encounter_data["epr_encounter_id"]
    )

    # Process the encounter update message to ensure Encounters API is up to date.
    master_encounter: Dict = _process_encounter_update(
        encounter_update_details=encounter_data,
        open_local_encounters=open_local_encounters,
        epr_encounters=epr_encounters,
        score_system_default_for_location=score_system_default_for_location,
    )

    # Process any merges of remaining encounters, or of patient records.
    remaining_encounters = [
        e
        for e in epr_encounters + open_local_encounters
        if e["uuid"] != master_encounter["uuid"]
    ]
    _process_encounter_merges(
        remaining_encounters=remaining_encounters,
        master_encounter_uuid=master_encounter["uuid"],
    )

    # If a patient merge request was made, link encounters between merged patients.
    if merge_patient_record_uuid:
        encounters_api.merge_patient_encounters(
            child_record_uuid=merge_patient_record_uuid,
            parent_record_uuid=encounter_data["patient_record_uuid"],
            parent_patient_uuid=patient_uuid,
            message_uuid=connector_message_id,
        )

    # If the patient is deceased, ensure encounter is discharged.
    if patient_deceased and not encounter_data.get("discharged_at"):
        logger.debug(
            "Patient '%s' is deceased, discharging encounter (%s)",
            patient_uuid,
            ROUTING_KEY,
        )
        encounters_api.update_encounter_by_uuid(
            encounter_uuid=master_encounter["uuid"],
            encounter_data={"discharged_at": generate_iso8601_timestamp()},
        )

    if encounter_data["deleted_at"]:
        logger.debug(
            "Publishing message to check deleted encounter for orphaned observations (%s)",
            ROUTING_KEY,
        )
        _publish_check_orphaned_observations(
            connector_message_id=connector_message_id,
            encounter_uuid=master_encounter["uuid"],
            patient_uuid=patient_uuid,
        )
    else:
        logger.debug("Marking HL7 message as fully processed (%s)", ROUTING_KEY)
        connector_api.patch_hl7_message(
            message_uuid=connector_message_id,
            message_body={"is_processed": True},
        )


def _extract_encounter_data(process_encounter_message: Dict) -> Dict:
    action: Dict = actions.extract_action(
        message=process_encounter_message, action_name="process_encounter"
    )
    encounter_data = EncounterUpdateMessage().load(action["data"], unknown=EXCLUDE)
    if encounter_data.pop("discharge_cancelled", False) is True:
        encounter_data["discharged_at"] = None
    if encounter_data.pop("admission_cancelled", False) is True:
        encounter_data["deleted_at"] = generate_iso8601_timestamp()
    else:
        encounter_data["deleted_at"] = None
    return encounter_data


def _process_encounter_update(
    encounter_update_details: Dict,
    open_local_encounters: List[Dict],
    epr_encounters: List[Dict],
    score_system_default_for_location: str,
) -> Dict:
    """
    Processes the details of an encounter update received via HL7 message from a trust,
    checks what encounters already exist, and returns the encounter that was updated.

    There are three cases here, depending on whether there are encounters matching
    the "epr_encounter_id" in the update ("EPR encounters"), and whether there are
    any open encounters without an "epr_encounter_id" ("open local encounters").

    If we end up creating a location, use the location's default score system.
    """
    # Case 1: There is an EPR encounter -> update EPR encounter
    if len(epr_encounters) > 0:
        latest_epr_encounter: Dict = epr_encounters[0]
        logger.debug(
            "EPR encounter '%s' found - updating (%s)",
            latest_epr_encounter["uuid"],
            ROUTING_KEY,
        )
        return encounters_api.update_encounter_by_uuid(
            latest_epr_encounter["uuid"], encounter_update_details
        )

    # Case 2: No EPR encounter, no open local encounter -> create new EPR encounter
    if len(open_local_encounters) == 0:
        logger.debug(
            "No EPR encounter, no open local encounter - creating (%s)",
            ROUTING_KEY,
        )
        # We're creating a new encounter, so set the score system to the location's default (if it's not already set)
        new_encounter_details = {
            "score_system": score_system_default_for_location,
            **encounter_update_details,
        }
        return encounters_api.create_encounter(new_encounter_details)

    # Case 3: No EPR encounter, open local encounter -> update open local encounter to EPR encounter
    logger.debug(
        "No EPR encounter, open local encounter found - updating (%s)",
        ROUTING_KEY,
    )
    latest_local_encounter: Dict = open_local_encounters.pop(0)
    return encounters_api.update_encounter_by_uuid(
        latest_local_encounter["uuid"], encounter_update_details
    )


def _process_encounter_merges(
    remaining_encounters: List[Dict],
    master_encounter_uuid: str,
) -> None:
    """
    Merges remaining encounters with the new master encounter. Remaining encounters will exist
    if there were multiple EPR encounters originally found, or if there are still open local
    encounters.
    """
    if len(remaining_encounters) > 0:
        logger.debug(
            "Merging remaining encounters with encounter '%s' (%s)",
            master_encounter_uuid,
            ROUTING_KEY,
        )
        encounters_api.merge_encounters_with_parent(
            remaining_encounters, master_encounter_uuid
        )


def _publish_check_orphaned_observations(
    connector_message_id: str, encounter_uuid: str, patient_uuid: str
) -> None:
    processed_msg = {
        "dhos_connector_message_uuid": connector_message_id,
        "actions": [
            {
                "name": "check_for_orphaned_observations",
                "data": {
                    "encounter_uuid": encounter_uuid,
                    "patient_uuid": patient_uuid,
                },
            }
        ],
    }
    kombu_batteries_included.publish_message(
        routing_key=check_orphaned_observations.ROUTING_KEY, body=processed_msg
    )
