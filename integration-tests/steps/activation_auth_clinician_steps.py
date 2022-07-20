import json
import random
import uuid
from typing import Dict

from behave import then, when
from behave.runner import Context
from clients import dhos_client, rabbitmq_client
from helpers.retry_asserts import assert_stops_raising


@when("a create activation auth clinician message is published to the broker")
def publish_sms_message(context: Context) -> None:

    context.clinician_uuid = str(uuid.uuid4())
    context.clinician_send_entry_identifier = str(random.randint(100000, 999999))
    routing_key = "dhos.D9000001"
    clinician: Dict = {
        "uuid": context.clinician_uuid,
        "send_entry_identifier": context.clinician_send_entry_identifier,
        "contract_expiry_eod_date": None,
        "login_active": True,
        "products": [{"product_name": "SEND"}],
        "groups": ["SEND Superclinician"],
    }
    rabbitmq_client.publish_message(
        connection=context.rabbitmq_connection,
        exchange=context.rabbitmq_exchange,
        message=json.dumps(clinician),
        routing_key=routing_key,
    )
    context.clinician = clinician


@then("the clinician can get a JWT from Activation Auth API")
def retry_retrieve_sms_events(context: Context) -> None:
    def retrieve_sms_events(context: Context) -> None:
        response = dhos_client.get_activation_auth_clinician_jwt(
            send_entry_identifier=context.clinician_send_entry_identifier,
            jwt=context.device_jwt,
        )
        assert response.status_code == 200
        assert "jwt" in response.json()

    assert_stops_raising(
        fn=retrieve_sms_events,
        args=(context,),
        exception_type=AssertionError,
    )
