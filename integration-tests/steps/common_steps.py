import uuid

from behave import given, then, use_fixture, when
from behave.runner import Context
from clients import rabbitmq_client, wiremock_client
from clients.rabbitmq_client import (
    create_rabbitmq_connection,
    create_rabbitmq_dlx_exchange,
)
from helpers.locations import create_location
from helpers.retry_asserts import assert_stops_raising
from helpers.security import generate_device_jwt, generate_system_jwt
from kombu import Message


@given("a system JWT")
def get_system_jwt(context: Context) -> None:
    if not hasattr(context, "system_jwt"):
        context.system_jwt = generate_system_jwt()


@given("a SEND device JWT")
def get_device_jwt(context: Context) -> None:
    if not hasattr(context, "device_jwt"):
        context.device_jwt = generate_device_jwt(context)


@given("a connection to rabbitmq")
def create_rabbitmq_infrastructure(context: Context) -> None:
    if not hasattr(context, "rabbitmq_connection"):
        use_fixture(create_rabbitmq_connection, context=context)
        use_fixture(create_rabbitmq_dlx_exchange, context=context)


@given("the Trustomer API is up and running")
def setup_trustomer_api_mock(context: Context) -> None:
    # Mock the Trustomer API
    wiremock_client.setup_mock_get_trustomer_config()


@given("the PDF API is up and running")
def setup_endpoint_pdf_api_send(context: Context) -> None:
    # Mock the PDF API due to dependencies on the PDF engine service.
    wiremock_client.setup_mock_pdf_api_send()
    wiremock_client.setup_mock_pdf_api_gdm()
    wiremock_client.setup_mock_pdf_api_ward()


@given("the Aggregator API is up and running")
def setup_endpoint_aggregator_api_send_pdf_data(context: Context) -> None:
    if not hasattr(context, "location_uuid"):
        context.location_uuid = str(uuid.uuid4())
    wiremock_client.setup_mock_aggregator_api_ward_report_data(
        location_uuid=context.location_uuid
    )


@given("the Services API is up and running")
def setup_endpoint_services_api_get_patient(context: Context) -> None:
    context.patient_uuid = str(uuid.uuid4())
    context.product_uuid = str(uuid.uuid4())
    context.patient_record_uuid = str(uuid.uuid4())
    wiremock_client.setup_mock_services_api_get_patient(
        location_uuid=context.location_uuid
    )
    wiremock_client.setup_mock_services_api_patch_patient(
        record_uuid=context.patient_record_uuid, product_uuid=context.product_uuid
    )
    wiremock_client.setup_mock_services_api_get_patient_by_record(
        patient_uuid=context.patient_uuid,
        record_uuid=context.patient_record_uuid,
        product_uuid=context.product_uuid,
    )
    wiremock_client.setup_mock_services_api_get_patients_by_identifier(
        patient_uuid=context.patient_uuid,
        record_uuid=context.patient_record_uuid,
        product_uuid=context.product_uuid,
    )
    wiremock_client.setup_mock_users_api_get_clinician()
    wiremock_client.setup_mock_users_api_retrieve_clinician_list()


@given('a location called "{name}" exists')
def setup_endpoint_locations_api(context: Context, name: str) -> None:
    context.location_uuid, context.location_ods_code = create_location(
        context, name=name
    )


@when("an invalid {routing_key} message is published to the broker")
def publish_invalid_message(context: Context, routing_key: str) -> None:
    context.message_identifier = str(uuid.uuid4())
    rabbitmq_client.publish_message(
        connection=context.rabbitmq_connection,
        exchange=context.rabbitmq_exchange,
        message="invalid message body",
        routing_key=routing_key,
        message_identifier=context.message_identifier,
    )


@then("the message goes to the error queue")
def retry_validate_message_on_error_queue(context: Context) -> None:
    def validate_message_on_error_queue(context: Context) -> None:
        message: Message = rabbitmq_client.get_message_on_queue(
            queue=context.rabbitmq_error_queue, context=context
        )
        assert message.headers["x-message-identifier"] == context.message_identifier

    assert_stops_raising(
        fn=validate_message_on_error_queue,
        args=(context,),
        exception_type=AssertionError,
    )
