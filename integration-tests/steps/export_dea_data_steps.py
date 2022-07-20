import json
from typing import Dict, List

from behave import given, then, when
from behave.runner import Context
from clients import rabbitmq_client, wiremock_client
from helpers.retry_asserts import assert_stops_raising


@given("the DEA Ingest API is up and running")
def setup_mock_dea_ingest_api(context: Context) -> None:
    wiremock_client.setup_mock_dea_ingest_api()


@given("the DEA Auth0 tenant is up and running")
def setup_mock_dea_auth0_tenant(context: Context) -> None:
    wiremock_client.setup_mock_dea_auth0_tenant()


@when("an export GDM SYNE BG readings message is published to the broker")
def publish_export_gdm_sync_bg_readings_message(context: Context) -> None:
    routing_key = "dhos.DM000015"
    export_gdm_syne_bg_readings_message: List[Dict] = [
        {
            "reading_id": "5d505813-1152-4466-945e-9ef1d09c1e55",
            "patient_id": "011a35d9-f0ab-44f6-85b4-397d1f4d593f",
            "bg_reading_datetime": "2020-04-27T14:16:25.474Z",
            "prandial_tag": "other",
            "blood_glucose_value": 3.0,
            "meds_taken_flag": False,
            "sct_code": ["11687002"],
            "first_bg_reading_pre_seven_days_flag": False,
        },
        {
            "reading_id": "0f4f250f-36f7-407a-8b92-42757961785e",
            "patient_id": "011a35d9-f0ab-44f6-85b4-397d1f4d593f",
            "bg_reading_datetime": "2020-04-25T14:16:27.395Z",
            "prandial_tag": "other",
            "blood_glucose_value": 3.0,
            "meds_taken_flag": False,
            "sct_code": ["11687002"],
            "first_bg_reading_pre_seven_days_flag": False,
        },
    ]
    rabbitmq_client.publish_message(
        connection=context.rabbitmq_connection,
        exchange=context.rabbitmq_exchange,
        message=json.dumps(export_gdm_syne_bg_readings_message),
        routing_key=routing_key,
    )


@then("the DEA Ingest API has received an export request with data type {data_type}")
def retry_check_mock_dea_ingest_api_called(context: Context, data_type: str) -> None:
    def check_mock_dea_ingest_api_called(data_type: str) -> None:
        calls: List[Dict] = wiremock_client.get_mock_dea_ingest_api_calls()
        data_types = [
            json.loads(c.get("body", {})).get("metadata", {}).get("data_type")
            for c in calls
        ]
        assert len([d for d in data_types if d == data_type]) == 1

    assert_stops_raising(
        fn=check_mock_dea_ingest_api_called,
        args=(data_type,),
        exception_type=AssertionError,
    )
