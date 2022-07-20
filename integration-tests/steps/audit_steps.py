import json
from typing import Any, Dict

from behave import then, when
from behave.runner import Context
from clients import dhos_client, rabbitmq_client
from helpers.retry_asserts import assert_stops_raising


@when("an audit event is published to the broker")
def publish_audit_event(context: Context) -> None:
    routing_key = "dhos.34837004"
    audit_event: Dict[str, Any] = {
        "event_type": "some_event_type",
        "event_data": {
            "some_field": "some_value",
            "some_other_field": "Some other value",
        },
    }
    rabbitmq_client.publish_message(
        connection=context.rabbitmq_connection,
        exchange=context.rabbitmq_exchange,
        message=json.dumps(audit_event),
        routing_key=routing_key,
    )

    context.audit_event_type = audit_event["event_type"]


@then("the event is stored in the Audit API")
def retry_retrieve_audit_event(context: Context) -> None:
    def retrieve_audit_event(context: Context) -> None:
        response = dhos_client.get_audit_events(context.system_jwt)
        response.raise_for_status()
        matching_event = next(
            (e for e in response.json() if e["event_type"] == context.audit_event_type),
            None,
        )
        assert matching_event is not None

    assert_stops_raising(
        fn=retrieve_audit_event,
        args=(context,),
        exception_type=AssertionError,
    )
