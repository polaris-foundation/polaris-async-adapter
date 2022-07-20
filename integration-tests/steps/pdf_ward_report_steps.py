import json
from typing import Dict, List

from behave import then, when
from behave.runner import Context
from clients import rabbitmq_client, wiremock_client
from helpers.retry_asserts import assert_stops_raising


@when("an aggregate ward report PDF message is published to the broker")
def publish_send_ward_report_pdf_message(context: Context) -> None:
    message: Dict = {
        "start_date": "2019-01-01T00:00:00.000Z",
        "end_date": "2019-02-01T00:00:00.000Z",
    }
    routing_key = "dhos.DM000010"
    rabbitmq_client.publish_message(
        connection=context.rabbitmq_connection,
        exchange=context.rabbitmq_exchange,
        message=json.dumps(message),
        routing_key=routing_key,
    )


@then("the ward report PDF data is aggregated")
def retry_check_ward_report_data_aggregated(context: Context) -> None:
    def check_ward_report_data_aggregated() -> None:
        calls: List[
            Dict
        ] = wiremock_client.get_mock_aggregator_api_ward_report_data_calls()
        assert len(calls) == 1

    assert_stops_raising(
        fn=check_ward_report_data_aggregated,
        exception_type=AssertionError,
    )


@then("a new ward report PDF has been created")
def retry_check_new_ward_report_pdf_message(context: Context) -> None:
    def check_new_ward_report_pdf_message() -> None:
        calls: List[Dict] = wiremock_client.get_mock_pdf_api_ward_calls()
        ward_name = [json.loads(c.get("body", {})).get("ward_name") for c in calls]
        assert len(ward_name) == 1

    assert_stops_raising(
        fn=check_new_ward_report_pdf_message,
        exception_type=AssertionError,
    )
