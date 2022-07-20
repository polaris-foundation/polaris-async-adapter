import logging
from datetime import datetime, timezone
from typing import Dict, List

from behave import given, then, when
from behave.runner import Context
from clients import dhos_client
from helpers.retry_asserts import assert_stops_raising

logger = logging.getLogger("Tests")


def _create_reading(patient_uuid: str, jwt: str) -> None:
    reading = {
        "blood_glucose_value": 12.0,
        "comment": "Sample reading comment",
        "doses": [],
        "measured_timestamp": datetime.now(tz=timezone.utc).isoformat(
            timespec="milliseconds"
        ),
        "prandial_tag": {"uuid": "PRANDIAL-TAG-AFTER-BREAKFAST", "value": 2},
        "banding_id": "BG-READING-BANDING-HIGH",
        "reading_metadata": {"control": False, "manual": False},
        "units": "mmol/L",
    }
    response = dhos_client.create_reading(
        patient_uuid=patient_uuid,
        reading_details=reading,
        jwt=jwt,
    )
    assert response.status_code == 200


@given("a patient has a recent abnormal BG reading")
def create_abnormal_reading(context: Context) -> None:
    _create_reading(patient_uuid=context.patient_uuid, jwt=context.system_jwt)


@when("the patient records another abnormal BG reading")
def create_another_reading(context: Context) -> None:
    _create_reading(patient_uuid=context.patient_uuid, jwt=context.system_jwt)


@then("the reading results in an amber alert")
def retry_check_amber_alert(context: Context) -> None:
    def check_amber_alert(context: Context) -> None:
        response = dhos_client.get_bg_readings_patient(
            patient_uuid=context.patient_uuid, jwt=context.system_jwt
        )
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["current_amber_alert"] is True

    assert_stops_raising(
        fn=check_amber_alert,
        args=(context,),
        exception_type=AssertionError,
    )


@then("a new glucose alert message has been created")
def retry_check_new_glucose_alert_message(context: Context) -> None:
    def check_new_glucose_alert_message(context: Context) -> None:
        response = dhos_client.get_message_by_sender_and_receiver_id(
            sender_id=context.patient_uuid,
            receiver_id=context.location_uuid,
            jwt=context.system_jwt,
        )
        assert response.status_code == 200
        messages: List[Dict] = response.json()
        assert len(messages) > 0
        assert (
            messages[0]["content"]
            == f"Laura has posted at least 2 out of threshold readings within the past 2 days where readings were taken"
        )
        assert messages[0]["message_type"]["value"] == 8

    assert_stops_raising(
        fn=check_new_glucose_alert_message,
        args=(context,),
        exception_type=AssertionError,
    )
