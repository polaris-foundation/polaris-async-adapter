import json
from typing import Dict, List

from behave import then, when
from behave.runner import Context
from clients import rabbitmq_client, wiremock_client
from helpers.retry_asserts import assert_stops_raising


@when("an aggregate SEND PDF message is published to the broker")
def publish_send_report_pdf_message(context: Context) -> None:
    message: Dict = {"encounter_id": context.encounter_uuid}
    routing_key = "dhos.DM000007"
    rabbitmq_client.publish_message(
        connection=context.rabbitmq_connection,
        exchange=context.rabbitmq_exchange,
        message=json.dumps(message),
        routing_key=routing_key,
    )


@then("a new SEND encounter report PDF has been created")
def retry_check_new_send_report_pdf_message(context: Context) -> None:
    encounter_uuid: str = context.encounter_uuid

    def check_new_send_report_pdf_message() -> None:
        calls: List[Dict] = wiremock_client.get_mock_pdf_api_send_calls()
        encounter_request_bodies: List[Dict] = [
            json.loads(c.get("body", {})).get("encounter") for c in calls
        ]
        matching_requests: List[Dict] = [
            e for e in encounter_request_bodies if e["uuid"] == encounter_uuid
        ]
        # It may be more than one because depending on the timing of the setup steps (which involve
        # posting obs, which triggers the PDF generation again!) it might have been called multiple times
        assert len(matching_requests) > 0

    assert_stops_raising(
        fn=check_new_send_report_pdf_message,
        exception_type=AssertionError,
    )
