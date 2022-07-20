from datetime import datetime, timezone
from typing import Any, AnyStr, Dict, List, Set

from marshmallow import Schema, fields
from she_logging import logger

from dhos_async_adapter.clients import (
    encounters_api,
    locations_api,
    observations_api,
    pdf_api,
    services_api,
    users_api,
)
from dhos_async_adapter.helpers.validation import validate_message_body_dict

ROUTING_KEY = "dhos.DM000007"


class GenerateSendPdfMessage(Schema):
    encounter_id = fields.String(required=True)


def process(body: AnyStr) -> None:
    """
    - Summary: Generate summary report PDF on a SEND encounter (hospital stay).
    - Routing Key: dhos.DM000007
    - Body: An object containing an encounter ID.
    - Notes: Generates ward report PDFs containing observation statistics
    - Endpoint(s):
      - GET /dhos-encounters/dhos/v1/encounter/<encounter_uuid>
      - GET /dhos-encounters/dhos/v1/encounter/<encounter_uuid>/children
      - GET /dhos-services/dhos/v1/patient/record/<record_uuid>
      - GET /dhos-locations/dhos/v1/location/<location_uuid>
      - GET /dhos-observations/dhos/v2/observation_set
      - POST /dhos-users/dhos/v1/clinician_list
      - POST /dhos-pdf/dhos/v1/send_pdf
    """
    logger.info("Received 'aggregate SEND PDF data' message (%s)", ROUTING_KEY)

    # Load and validate message body.
    logger.debug(
        "Aggregate SEND PDF data message body (%s)",
        ROUTING_KEY,
        extra={"message_body": body},
    )
    aggregate_message: Dict = validate_message_body_dict(
        body=body, schema=GenerateSendPdfMessage
    )

    # Get aggregated data for SEND PDF.
    aggregated_data: Dict[str, Any] = _aggregate_send_pdf_data(
        encounter_uuid=aggregate_message["encounter_id"]
    )

    # Trigger PDF generation
    logger.info(
        "Triggering SEND PDF generation for encounter with UUID %s",
        aggregated_data["encounter"]["uuid"],
    )
    pdf_api.post_send_pdf(message_body=aggregated_data)


def _aggregate_send_pdf_data(encounter_uuid: str) -> Dict[str, Any]:
    encounter: Dict = encounters_api.get_encounter_by_uuid(
        encounter_uuid=encounter_uuid, show_deleted=True
    )
    child_encounter_uuids: List[str] = encounters_api.get_child_encounters(
        encounter_uuid, show_deleted=True
    )
    patient: Dict = services_api.get_patient_by_record_id(
        record_uuid=encounter["patient_record_uuid"]
    )
    location: Dict = locations_api.get_location_by_uuid(
        location_uuid=encounter["location_uuid"]
    )
    all_encounter_uuids: Set[str] = {encounter_uuid, *child_encounter_uuids}
    observation_sets: List[
        Dict
    ] = observations_api.get_observation_sets_for_encounter_ids(
        encounter_uuids=list(all_encounter_uuids)
    )

    # Update observation sets to inflate each created_by field with clinician info (where possible).
    clinician_uuids: Set[str] = set(o["created_by"] for o in observation_sets)
    score_system_history: List[Dict] = encounter.get("score_system_history", [])
    clinician_uuids |= {
        score_change["created_by"]
        for score_change in score_system_history
        if isinstance(score_change["created_by"], str)
    }
    clinicians: Dict[str, Dict] = users_api.get_clinicians_by_uuids(
        clinician_uuids=list(clinician_uuids), compact=True
    )
    for obs_set in observation_sets:
        clinician_uuid: str = obs_set["created_by"]
        # API returns null for dhos-robot (or other system ids)
        clinician_detail: Dict = clinicians.get(clinician_uuid) or {}
        obs_set["created_by"] = {
            "uuid": clinician_uuid,
            "first_name": clinician_detail.get("first_name") or "",
            "last_name": clinician_detail.get("last_name") or "",
        }

    for score_change in score_system_history:
        clinician_uuid = score_change["created_by"]
        if clinician_uuid is None:
            # API returns null for dhos-robot (or other system ids)
            score_change["changed_by"] = {
                "uuid": None,
                "first_name": "",
                "last_name": "",
            }
        elif isinstance(clinician_uuid, str):
            clinician_detail = clinicians.get(clinician_uuid) or {}
            score_change["changed_by"] = {
                "uuid": clinician_uuid,
                "first_name": clinician_detail.get("first_name") or "",
                "last_name": clinician_detail.get("last_name") or "",
            }

    iso8601_timestamp: str = (
        datetime.utcnow()
        .replace(tzinfo=timezone.utc)
        .isoformat(timespec="milliseconds")
    )

    return {
        "aggregation_time": iso8601_timestamp,
        "encounter": encounter,
        "patient": patient,
        "location": location,
        "observation_sets": observation_sets,
    }
