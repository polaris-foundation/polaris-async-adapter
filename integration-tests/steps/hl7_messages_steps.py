import json
import logging
import random
import string
import uuid
from typing import Any, Dict, List, Optional

from behave import given, then, when
from behave.runner import Context
from clients import dhos_client, rabbitmq_client, wiremock_client
from helpers.locations import create_hl7_test_ward
from helpers.retry_asserts import assert_stops_raising

logger = logging.getLogger("Tests")


@given("an existing encounter")
def create_encounter(context: Context) -> None:
    encounter = {
        "encounter_type": "INPATIENT",
        "admitted_at": "2019-01-01T00:00:00.000Z",
        "location_uuid": context.location_uuid,
        "patient_record_uuid": context.patient_record_uuid,
        "patient_uuid": context.patient_uuid,
        "dh_product_uuid": context.product_uuid,
        "score_system": "news2",
    }
    response = dhos_client.create_encounter(encounter=encounter, jwt=context.system_jwt)
    assert response.status_code == 200
    context.encounter_uuid = response.json()["uuid"]


@given("the Connector API is up and running")
def setup_endpoint_update_hl7_process_status(context: Context) -> None:
    # This integration tests only a part of the HL7 message processing
    # i.e. after the patient and encounter records have been created.
    # Mock the Connector API as the corresponding HL7 message record in the connector-api database does not exist.
    wiremock_client.setup_mock_connector_api_patch_hl7()
    wiremock_client.setup_mock_connector_api_post_oru()


@given("the encounter has observations")
def create_obs_sets_for_encounter(context: Context) -> None:
    obs_set = {
        "empty_set": False,
        "encounter_id": context.encounter_uuid,
        "is_partial": False,
        "location": "285c1c51-5d72-4066-b1da-49604a3f21b0",
        "monitoring_instruction": "medium_monitoring",
        "observations": [
            {
                "measured_time": "2017-09-23T08:29:19.123+00:00",
                "observation_type": "heart_rate",
                "observation_unit": "bpm",
                "observation_value": 58,
                "patient_refused": False,
                "score_value": 4,
            }
        ],
        "obx_abnormal_flags": "HIGH",
        "obx_reference_range": "0-4",
        "ranking": "0101010,2017-09-23T08:29:19.123+00:00",
        "record_time": "2017-09-23T08:31:19.123+00:00",
        "score_severity": "high",
        "score_string": "12C",
        "score_system": "news2",
        "score_value": 12,
        "spo2_scale": 2,
        "time_next_obs_set_due": "2019-01-23T08:31:19.123+00:00",
    }
    response = dhos_client.post_observation_set(obs_set, jwt=context.system_jwt)
    assert response.status_code == 200


@when("an encounters obs set notification message is published to the broker")
def publish_encounter_obs_set_notification_message(context: Context) -> None:
    context.observation_set_uuid = str(uuid.uuid4())
    context.clinician_uuid = str(uuid.uuid4())
    notification_message = {
        "actions": [
            {
                "name": "process_observation_set",
                "data": {
                    "observation_set": {
                        "created": "2019-01-31T09:47:27.123Z",
                        "created_by": context.clinician_uuid,
                        "encounter_id": context.encounter_uuid,
                        "is_partial": False,
                        "modified": "2019-01-31T09:47:27.123Z",
                        "monitoring_instruction": "some monitoring instruction",
                        "observations": [
                            {
                                "created": "2019-01-31T09:47:27.089Z",
                                "measured_time": "2019-01-30T13:07:26.870Z",
                                "modified": "2019-01-31T09:47:27.089Z",
                                "observation_metadata": None,
                                "observation_type": "spo2",
                                "observation_unit": "%",
                                "observation_value": 94,
                                "score_value": 0,
                                "uuid": "d449bc4f-b730-4ee2-b2a9-d1f70d8acab6",
                            },
                        ],
                        "record_time": "2019-01-30T13:06:26.870Z",
                        "score_severity": "medium",
                        "score_string": "3",
                        "score_system": "news2",
                        "score_value": 3,
                        "spo2_scale": 1,
                        "time_next_obs_set_due": None,
                        "uuid": context.observation_set_uuid,
                    }
                },
            }
        ]
    }
    routing_key = "dhos.DM000004"
    rabbitmq_client.publish_message(
        connection=context.rabbitmq_connection,
        exchange=context.rabbitmq_exchange,
        message=json.dumps(notification_message),
        routing_key=routing_key,
    )


@when("a patient update message involving a {update_type} is published to the broker")
def publish_encounter_update_message(context: Context, update_type: str) -> None:
    context.dhos_connector_message_uuid = str(uuid.uuid4())
    context.epr_encounter_id = "2020L" + "".join(
        random.choice(string.digits) for _ in range(12)
    )
    extra_encounter_details: Dict[str, Any] = {}
    if update_type == "discharge":
        context.encounter_discharge_date = "2020-01-02T00:00:00.000Z"
        extra_encounter_details["discharged_at"] = context.encounter_discharge_date
    if update_type == "cancelled admission":
        extra_encounter_details["admission_cancelled"] = True
    encounter_update_message = {
        "dhos_connector_message_uuid": context.dhos_connector_message_uuid,
        "actions": [
            {
                "name": "process_patient",
                "data": {
                    "first_name": "STEPHEN",
                    "last_name": "ZZZEDUCATION",
                    "sex_sct": "248153007",
                    "nhs_number": "4902374218",
                    "mrn": "1218357",
                    "date_of_birth": "1982-11-03",
                },
            },
            {
                "name": "process_location",
                "data": {
                    "location": {
                        "epr_ward_code": "NOC-Ward B",
                        "epr_bay_code": "Day Room",
                        "epr_bed_code": "Chair 6",
                    }
                },
            },
            {
                "name": "process_encounter",
                "data": {
                    "epr_encounter_id": context.epr_encounter_id,
                    "location": {
                        "epr_ward_code": "NOC-Ward B",
                        "epr_bay_code": "Day Room",
                        "epr_bed_code": "Chair 6",
                    },
                    "encounter_type": "INPATIENT",
                    "admitted_at": "2020-01-01T00:00:00.000Z",
                    "transfer_cancelled": False,
                    "discharge_cancelled": False,
                    "encounter_moved": False,
                    "patient_deceased": False,
                    "merge_patient_record_uuid": None,
                    **extra_encounter_details,
                },
            },
        ],
    }
    routing_key = "dhos.24891000000101"
    rabbitmq_client.publish_message(
        connection=context.rabbitmq_connection,
        exchange=context.rabbitmq_exchange,
        message=json.dumps(encounter_update_message),
        routing_key=routing_key,
    )


@then("a new encounter has been created")
def retry_check_new_encounter(context: Context) -> None:
    def check_new_encounter(context: Context) -> None:
        response = dhos_client.get_encounters_by_epr_id(
            patient_uuid=context.patient_uuid,
            epr_encounter_id=context.epr_encounter_id,
            jwt=context.system_jwt,
        )
        assert response.status_code == 200
        encounters: List[Dict] = response.json()
        assert len(encounters) == 1

    assert_stops_raising(
        fn=check_new_encounter,
        args=(context,),
        exception_type=AssertionError,
    )


@then("the encounter is marked as discharged")
def retry_check_encounter_discharged(context: Context) -> None:
    def check_encounter_discharged(context: Context) -> None:
        response = dhos_client.get_encounter_by_uuid(
            encounter_uuid=context.encounter_uuid,
            jwt=context.system_jwt,
        )
        assert response.status_code == 200
        assert response.json()["discharged_at"] == context.encounter_discharge_date

    assert_stops_raising(
        fn=check_encounter_discharged,
        args=(context,),
        exception_type=AssertionError,
    )


@then("the encounter is deleted and merged with a discharged local encounter")
def retry_check_encounter_deleted(context: Context) -> None:
    def check_encounter_deleted(context: Context) -> None:
        response = dhos_client.get_encounter_by_uuid(
            encounter_uuid=context.encounter_uuid,
            show_deleted=True,
            jwt=context.system_jwt,
        )
        assert response.status_code == 200
        assert response.json()["deleted_at"] not in (None, "")
        child_of_encounter_uuid: Optional[str] = response.json().get(
            "child_of_encounter_uuid"
        )
        assert child_of_encounter_uuid not in (None, "")
        parent_response = dhos_client.get_encounter_by_uuid(
            encounter_uuid=child_of_encounter_uuid,
            jwt=context.system_jwt,
        )
        assert parent_response.status_code == 200
        assert parent_response.json()["discharged_at"] not in (None, "")
        context.new_local_encounter_uuid = child_of_encounter_uuid

    assert_stops_raising(
        fn=check_encounter_deleted,
        args=(context,),
        exception_type=AssertionError,
    )


@then("the HL7 message has been marked as processed")
def retry_check_mock_connector_api_patch_hl7_called(context: Context) -> None:
    def check_mock_connector_api_patch_hl7_called(context: Context) -> None:
        calls: List[Dict] = wiremock_client.get_mock_connector_api_patch_hl7_calls(
            context.dhos_connector_message_uuid
        )
        is_processed = [
            json.loads(c.get("body", {})).get("is_processed") for c in calls
        ]
        assert len(is_processed) == 1

    assert_stops_raising(
        fn=check_mock_connector_api_patch_hl7_called,
        args=(context,),
        exception_type=AssertionError,
    )


@then("an HL7 ORU message is sent")
def retry_check_mock_connector_api_post_oru_called(context: Context) -> None:
    def check_mock_connector_api_post_oru_called() -> None:
        calls: List[Dict] = wiremock_client.get_mock_connector_api_post_oru_calls()
        actual_request_bodies: List[Dict] = [json.loads(c["body"]) for c in calls]
        actual_request_body = next(
            (
                r
                for r in actual_request_bodies
                if r["actions"][0]["data"]["observation_set"]["uuid"]
                == context.observation_set_uuid
            ),
            None,
        )
        assert actual_request_body is not None
        assert actual_request_body["actions"][0]["name"] == "process_observation_set"
        for k in ["observation_set", "encounter", "clinician", "patient"]:
            assert k in actual_request_body["actions"][0]["data"]
        assert (
            actual_request_body["actions"][0]["data"]["clinician"]["uuid"]
            == context.clinician_uuid
        )

    assert_stops_raising(
        fn=check_mock_connector_api_post_oru_called,
        exception_type=AssertionError,
    )


@given("a location set to use a default score system of {score_system}")
def set_default_score_system(context: Context, score_system: str) -> None:
    parsed_score_system: Optional[str] = (
        None if score_system == "NULL" else score_system
    )
    create_hl7_test_ward(context, parsed_score_system)


@then("the new encounter has a score system of {score_system}")
def validate_score_system(context: Context, score_system: str) -> None:
    def retry_validate_score_system() -> None:
        response = dhos_client.get_encounters_by_epr_id(
            patient_uuid=context.patient_uuid,
            epr_encounter_id=context.epr_encounter_id,
            jwt=context.system_jwt,
        )
        assert response.status_code == 200
        encounters: List[Dict] = response.json()
        assert len(encounters) == 1
        assert encounters[0]["score_system"] == score_system

    assert_stops_raising(
        fn=retry_validate_score_system,
        exception_type=AssertionError,
    )
