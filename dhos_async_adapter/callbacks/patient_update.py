from datetime import date
from typing import AnyStr, Dict, List, Optional, Tuple

import draymed
import kombu_batteries_included
from marshmallow import INCLUDE, Schema, fields
from she_logging import logger

from dhos_async_adapter.clients import connector_api, locations_api, services_api
from dhos_async_adapter.helpers import actions
from dhos_async_adapter.helpers.actions import ActionsMessage
from dhos_async_adapter.helpers.exceptions import RejectMessageError
from dhos_async_adapter.helpers.validation import validate_message_body_dict

ROUTING_KEY = "dhos.24891000000101"


class PatientUpdate(Schema):
    class Meta:
        unknown = INCLUDE

    previous_nhs_number = fields.String(required=False, allow_none=True)
    previous_hospital_number = fields.String(
        required=False, allow_none=True, data_key="previous_mrn"
    )
    dob = fields.String(required=False, allow_none=True, data_key="date_of_birth")
    dod = fields.String(required=False, allow_none=True, data_key="date_of_death")
    hospital_number = fields.String(required=False, allow_none=True, data_key="mrn")
    nhs_number = fields.String(required=False, allow_none=True)
    sex = fields.String(required=False, allow_none=True, data_key="sex_sct")


class Location(Schema):
    class Meta:
        unknown = INCLUDE

    epr_ward_code = fields.String(required=True)
    epr_bay_code = fields.String(required=False, allow_none=True)
    epr_bed_code = fields.String(required=False, allow_none=True)


class LocationUpdate(Schema):
    class Meta:
        unknown = INCLUDE

    location = fields.Nested(Location, required=False, allow_none=True)
    previous_location = fields.Nested(Location, required=False, allow_none=True)


def process(body: AnyStr) -> None:
    """
    - Summary: Processes a patient update received via HL7 messages, and updates Services API as appropriate.
    - Routing Key: dhos.24891000000101
    - Body: A group of actions in the format published by the Connector API service.
    - Notes: Creates or updates patients and locations as appropriate, then publishes dhos.305058001 or updates message in Connector API.
    - Endpoint(s):
        - GET /dhos-services/dhos/v1/patient
        - POST /dhos-services/dhos/v1/patient
        - PATCH /dhos-services/dhos/v1/patient/<patient_uuid>
        - GET /dhos-locations/dhos/v1/location/search
        - PATCH /dhos-connector/dhos/v1/message/<message_uuid>
    """
    logger.info("Received process patient message (%s)", ROUTING_KEY)

    # Load and validate message body.
    logger.debug(
        "Process patient message body (%s)",
        ROUTING_KEY,
        extra={"message_body": body},
    )
    update_patient_message: Dict = validate_message_body_dict(
        body=body, schema=ActionsMessage
    )
    connector_message_id: str = update_patient_message["dhos_connector_message_uuid"]

    logger.debug("Processing patient")
    primary_patient, child_patient = _process_patient(update_patient_message)

    logger.debug("Processing location")
    current_location, previous_location = _process_locations(update_patient_message)

    logger.debug("Processing encounter")
    encounter_action: Optional[Dict] = actions.extract_action_if_exists(
        message=update_patient_message, action_name="process_encounter"
    )
    if encounter_action is None:
        # The message contains no encounter information so we are finished processing it.
        logger.debug("Marking HL7 message as fully processed (%s)", ROUTING_KEY)
        connector_api.patch_hl7_message(
            message_uuid=connector_message_id,
            message_body={"is_processed": True},
        )
        return

    # We need to update the encounter with the info in Services API, and then republish.
    send_product_uuid: str = next(
        p for p in primary_patient["dh_products"] if p["product_name"].upper() == "SEND"
    )["uuid"]
    child_patient_record_uuid: Optional[str] = (
        (child_patient or {}).get("record", {}).get("uuid")
    )
    score_system_default: str = _get_score_system_default_for_location(current_location)
    encounter_action["data"].update(
        {
            "patient_uuid": primary_patient["uuid"],
            "patient_record_uuid": primary_patient["record"]["uuid"],
            "dh_product_uuid": send_product_uuid,
            "location_uuid": (current_location or {}).get("uuid"),
            "previous_location_uuid": (previous_location or {}).get("uuid"),
            "merge_patient_record_uuid": child_patient_record_uuid,
            "score_system_default_for_location": score_system_default,
        }
    )
    # 'update_patient_message' holds a reference to 'encounter_action', so we can just republish it directly.
    kombu_batteries_included.publish_message(
        routing_key="dhos.305058001", body=update_patient_message
    )


def _process_patient(update_patient_message: Dict) -> Tuple[Dict, Optional[Dict]]:
    """
    Processes the patient described in the update message. This may involve creating or updating
    a patient in Services API. It may also involve merging a patient, in which case the merged
    child patient will also be returned.
    """
    process_patient_action: Dict = actions.extract_action(
        message=update_patient_message, action_name="process_patient"
    )
    patient_data = PatientUpdate().load(process_patient_action["data"], unknown=INCLUDE)

    # Strip out fields we don't want, as well as empty and dict fields.
    previous_nhs_number: Optional[str] = patient_data.pop("previous_nhs_number", None)
    previous_hospital_number: Optional[str] = patient_data.pop(
        "previous_hospital_number", None
    )
    patient_data = {
        k: v
        for k, v in patient_data.items()
        if not isinstance(v, Dict) and v not in [None, ""]
    }

    # Try to get patient by identifier (NHS number first, then MRN).
    logger.debug("Looking for existing patient using identifiers")
    matched_patient: Optional[Dict] = _get_existing_patient(
        nhs_number=patient_data.get("nhs_number"),
        hospital_number=patient_data.get("hospital_number"),
    )
    existing_patient_uuid: Optional[str] = (
        None if matched_patient is None else matched_patient["uuid"]
    )

    # Update or create patient
    primary_patient: Dict = _update_or_create_patient(
        existing_patient_uuid, patient_data
    )

    # Process patient to merge if necessary.
    child_patient: Optional[Dict] = _process_patient_to_merge(
        primary_patient_uuid=primary_patient["uuid"],
        patient_data=patient_data,
        previous_nhs_number=previous_nhs_number,
        previous_hospital_number=previous_hospital_number,
    )

    return primary_patient, child_patient


def _process_locations(
    update_patient_message: Dict,
) -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Processes the locations described in the update message. This may involve creating locations in
    Services API.
    """
    process_location_action: Optional[Dict] = actions.extract_action_if_exists(
        message=update_patient_message, action_name="process_location"
    )
    if process_location_action is None:
        return None, None
    location_data = LocationUpdate().load(
        process_location_action["data"], unknown=INCLUDE
    )

    return (
        _process_single_location(location_data.get("location")),
        _process_single_location(location_data.get("previous_location")),
    )


def _process_single_location(location_data: Optional[Dict]) -> Optional[Dict]:
    """
    Builds a location's ODS code from the components in the input data, checks to see whether
    the location exists, and creates it (including possible parents) if it doesn't.
    """
    if location_data is None:
        return None

    # Build ODS code from components.
    ods_code: str = location_data["epr_ward_code"]
    if location_data.get("epr_bay_code"):
        ods_code += f":{location_data['epr_bay_code']}"
    if location_data.get("epr_bed_code"):
        ods_code += f":{location_data['epr_bed_code']}"

    matching_locations: Dict[str, Dict] = locations_api.get_locations_by_ods_code(
        ods_code
    )
    if len(matching_locations) > 1:
        logger.error(
            "Found multiple locations (%d) with the provided identifiers",
            len(matching_locations),
        )
        raise RejectMessageError()
    if len(matching_locations) == 1:
        _, location = matching_locations.popitem()
        return location

    # No matching location(s), create as appropriate.
    logger.debug("Creating locations by hierarchy from ODS code: %s", ods_code)
    return _create_location_hierarchy(ods_code)


def _create_location_hierarchy(ods_code: str) -> Optional[Dict]:
    """
    Creates a location hierarchy based on the ODS code provided. Locations that already exist
    will not be re-created. For example, an ODS code of WRD:BayA:Bed1 will create:
     - a ward with ODS code WRD and display name WRD
     - a bay with ODS code WRD:BayA and display name BayA
     - a bed with ODS code WRD:BayA:Bed1 and display name Bed1
    Returns the location node that is lowest (most specific) in the hierarchy - the bed, in the
    example above.
    """
    location_types: Tuple[str, str, str] = (
        draymed.codes.code_from_name("ward", category="location"),
        draymed.codes.code_from_name("bay", category="location"),
        draymed.codes.code_from_name("bed", category="location"),
    )
    logger.debug("Creating location hierarchy for ODS code %s", ods_code)
    hierarchy: List[str] = ods_code.split(":")
    this_node: Optional[Dict] = None
    parent_ods_code: Optional[str] = None
    for i in range(len(hierarchy)):
        current_ods_code = ":".join(hierarchy[: i + 1])
        logger.debug("Getting locations matching ods_code: %s", current_ods_code)
        matching_locations: Dict[str, Dict] = locations_api.get_locations_by_ods_code(
            current_ods_code
        )
        if len(matching_locations) > 1:
            logger.error(
                "Found multiple locations (%d) with the provided identifiers",
                len(matching_locations),
            )
            raise RejectMessageError()
        if len(matching_locations) == 1:
            logger.debug("Location with ODS code '%s' already exists", current_ods_code)
            _, this_node = matching_locations.popitem()
            parent_ods_code = current_ods_code
            continue

        # Need to create location
        logger.debug("Creating location with ODS code: %s", current_ods_code)
        location_details = {
            "ods_code": current_ods_code,
            "display_name": hierarchy[i],
            "location_type": location_types[i] if i < len(location_types) else "",
            "active": False,  # New locations created from EPR messages are inactive by default.
            "dh_products": [
                {
                    "product_name": "SEND",
                    "opened_date": date.today().isoformat(),
                }
            ],
        }
        if parent_ods_code:
            location_details["parent_ods_code"] = parent_ods_code
        this_node = locations_api.create_location(location_details)
        parent_ods_code = current_ods_code

    return this_node


def _get_existing_patient(
    nhs_number: Optional[str], hospital_number: Optional[str]
) -> Optional[Dict]:
    """
    Gets an existing patient from the Services API. Returns None if no patient is found.
    Checks first by NHS number, and then by hospital number if that fails.
    """
    if not nhs_number and not hospital_number:
        logger.error("Can not search for patient as MRN or NHS number is required")
        raise RejectMessageError()
    # Try to get patient by NHS number.
    if nhs_number:
        matching_patients_nhs_number: List[
            Dict
        ] = services_api.get_patients_by_identifier(
            identifier="nhs_number", identifier_value=nhs_number, product_name="SEND"
        )
        if matching_patients_nhs_number:
            logger.debug("Matched patient by NHS number")
            return matching_patients_nhs_number[0]

    # Try to get patient by hospital number.
    if hospital_number:
        matching_patients_hospital_number: List[
            Dict
        ] = services_api.get_patients_by_identifier(
            identifier="hospital_number",
            identifier_value=hospital_number,
            product_name="SEND",
        )
        if matching_patients_hospital_number:
            logger.debug("Matched patient by hospital number")
            return matching_patients_hospital_number[0]

    # No match.
    logger.debug("No match for patient identifiers")
    return None


def _update_or_create_patient(
    existing_patient_uuid: Optional[str], patient_data: Dict
) -> Dict:
    if existing_patient_uuid:
        logger.debug("Updating existing patient %s", existing_patient_uuid)
        return services_api.update_patient(
            patient_uuid=existing_patient_uuid, patient_details=patient_data
        )

    logger.debug("Creating new patient")
    patient_data["record"] = {}
    patient_data["dh_products"] = [
        {"product_name": "SEND", "opened_date": date.today().isoformat()}
    ]
    return services_api.create_patient(patient_details=patient_data)


def _process_patient_to_merge(
    primary_patient_uuid: str,
    patient_data: Dict,
    previous_nhs_number: Optional[str],
    previous_hospital_number: Optional[str],
) -> Optional[Dict]:
    """
    Processes the patient data to see whether a child patient needs to be merged.
    If there are previous patient identifiers to merge, creates/updates the child
    patient and then merges as appropriate.
    """
    if not previous_nhs_number and not previous_hospital_number:
        logger.debug("No patient to merge")
        return None
    patient_to_merge: Optional[Dict] = _get_existing_patient(
        nhs_number=previous_nhs_number, hospital_number=previous_hospital_number
    )
    if patient_to_merge:
        if patient_to_merge["uuid"] == primary_patient_uuid:
            # Patient has already been merged.
            logger.warning(
                "Patient %s appears to have already been merged",
                patient_to_merge["uuid"],
            )
            return None

        # Patch existing patient to parent
        return services_api.update_patient(
            patient_uuid=patient_to_merge["uuid"],
            patient_details={"child_of": primary_patient_uuid},
        )

    # Child patient needs to be created.
    merge_request_data = {
        k: v
        for k, v in patient_data.items()
        if not isinstance(v, Dict) and v not in [None, ""]
    }
    merge_request_data["nhs_number"] = previous_nhs_number or None
    merge_request_data["hospital_number"] = previous_hospital_number or None
    merge_request_data["child_of"] = primary_patient_uuid
    merge_request_data["record"] = {}
    return services_api.create_patient(patient_details=merge_request_data)


def _get_score_system_default_for_location(location: Optional[Dict]) -> str:
    """
    Extracts the default score system for the location or a parent location if necessary.
    Defaults to NEWS2 if no default is found in the location hierarchy.
    """
    while location is not None:
        logger.debug(
            "Looking for default score system for location %s", location["uuid"]
        )
        score_system_default: Optional[str] = location.get("score_system_default")
        if score_system_default is not None:
            logger.debug(
                "Found default score system %s for location %s",
                score_system_default,
                location["uuid"],
            )
            return score_system_default
        location = location.get("parent")

    logger.debug("No default score system for location hierarchy, defaulting to NEWS2")
    return "news2"
