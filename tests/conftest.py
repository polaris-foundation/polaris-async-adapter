import json
import re
import uuid
from typing import Any, Dict

import kombu_batteries_included
import pytest
import requests
from kombu import Connection, Exchange, Queue
from mock import Mock
from pytest_mock import MockFixture
from requests_mock import Mocker

from dhos_async_adapter.helpers import security


@pytest.fixture
def mock_exchange_init(mocker: MockFixture) -> Mock:
    return mocker.patch.object(Exchange, "__init__", return_value=None)


@pytest.fixture
def mock_queue_init(mocker: MockFixture) -> Mock:
    return mocker.patch.object(Queue, "__init__", return_value=None)


@pytest.fixture
def mock_connection_channel(mocker: MockFixture) -> Mock:
    return mocker.patch.object(Connection, "channel")


@pytest.fixture
def mock_get_request_headers(mocker: MockFixture) -> Mock:
    return mocker.patch.object(
        security, "get_request_headers", return_value={"Authorization": "Bearer TOKEN"}
    )


@pytest.fixture
def mock_publish(mocker: MockFixture) -> Mock:
    return mocker.patch.object(kombu_batteries_included, "publish_message")


@pytest.fixture
def connector_message_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def patient_uuid() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def clinician_uuid() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def epr_encounter_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def encounter_uuid() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def dhos_connector_message_uuid() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def location_uuid() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def patient_record_uuid() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def mock_encounter_post(requests_mock: Mocker) -> Mock:
    def callback(request: requests.Request, context: Any) -> Dict:
        return {**request.json(), "uuid": "new_encounter_uuid"}

    return requests_mock.post(
        f"http://dhos-encounters/dhos/v2/encounter",
        json=callback,
    )


@pytest.fixture
def mock_encounter_patch(requests_mock: Mocker) -> Mock:
    def callback(request: requests.Request, context: Any) -> Dict:
        encounter_uuid: str = request.url.split("/")[-1]
        return {**request.json(), "uuid": encounter_uuid}

    matcher = re.compile(r"^http://dhos-encounters/dhos/v1/encounter/[0-9a-zA-Z_\-]*$")
    return requests_mock.patch(matcher, json=callback)


@pytest.fixture
def mock_retrieve_dea_auth0_jwt(mocker: MockFixture) -> Mock:
    return mocker.patch.object(
        security, "_retrieve_dea_auth0_jwt", return_value="TOKEN"
    )


@pytest.fixture
def mock_dea_ingest_post(requests_mock: Mocker) -> Mock:
    return requests_mock.post("http://dea-ingest/dea/ingest/v2/dhos_data")


@pytest.fixture
def jane_deer() -> Dict[str, str]:
    return {
        "first_name": "Jane",
        "last_name": "Deer",
        "uuid": "82187d3a-208f-4903-a240-b1ad6a9ba5ae",
    }


@pytest.fixture
def moe_smith() -> Dict[str, str]:
    return {"first_name": "Moe", "last_name": "Smith", "uuid": str(uuid.uuid4())}


@pytest.fixture
def system_user() -> Dict[str, str]:
    return {"uuid": str(uuid.uuid4()), "first_name": "system", "last_name": "system"}


@pytest.fixture
def send_product(moe_smith: Dict) -> Dict:
    return {
        "closed_date": None,
        "closed_reason": None,
        "closed_reason_other": None,
        "created": "2018-12-24T14:52:17.706Z",
        "created_by": moe_smith,
        "modified": "2018-12-24T14:52:17.708Z",
        "modified_by": moe_smith,
        "opened_date": "2018-12-24",
        "product_name": "SEND",
        "uuid": "2d87cce2-53a5-4fcd-9d40-6de08fbed771",
    }


@pytest.fixture
def gdm_pdf_data() -> str:
    """Sample data to generate GDM PDF"""
    return json.dumps(
        {
            "medications": {"some": "value"},
            "patient": {
                "uuid": "f7464749-ffed-4fee-a8e6-12877d84d694",
                "first_name": "someone",
                "last_name": "else",
                "nhs_number": "12345",
            },
            "pregnancy": {"some": "value"},
            "readings_plan": {"some": "value"},
            "management_plan": {"some": "value"},
            "diabetes": {"some": "value"},
            "deliveries": [{"some": "value"}],
            "blood_glucose_readings": [{"some": "value"}],
            "latest_visit": {"some": "value"},
            "medication_plan": {"some": "value"},
        }
    )


@pytest.fixture
def gdm_pdf_data_with_none_nhs_number() -> str:
    """Sample data to generate GDM PDF"""
    return json.dumps(
        {
            "medications": {"some": "value"},
            "patient": {
                "uuid": "f7464749-ffed-4fee-a8e6-12877d84d694",
                "first_name": "someone",
                "last_name": "else",
                "nhs_number": None,
            },
            "pregnancy": {"some": "value"},
            "readings_plan": {"some": "value"},
            "management_plan": {"some": "value"},
            "diabetes": {"some": "value"},
            "deliveries": [{"some": "value"}],
            "blood_glucose_readings": [{"some": "value"}],
            "latest_visit": {"some": "value"},
            "medication_plan": {"some": "value"},
        }
    )


@pytest.fixture
def ward_report_pdf_data() -> Dict:
    """sample data for ward report"""
    return {
        "pdf_data": [{"some": "value", "other": "value"}],
        "report_month": "April",
        "report_year": "2019",
        "hospital_name": "some-thing",
        "ward_name": "other-thing",
        "location_uuid": "c6307afb-3688-44c8-86aa-d90b599a8c15",
    }


@pytest.fixture
def mock_hl7_message_patch(requests_mock: Mocker, connector_message_id: str) -> Mock:
    return requests_mock.patch(
        f"http://dhos-connector/dhos/v1/message/{connector_message_id}",
        json={"uuid": connector_message_id},
    )
