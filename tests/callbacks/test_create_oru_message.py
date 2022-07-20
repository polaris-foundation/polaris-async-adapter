import json
import uuid
from typing import Dict

import pytest
from _pytest.logging import LogCaptureFixture
from mock import Mock
from requests_mock import Mocker

from dhos_async_adapter.callbacks import create_oru_message
from dhos_async_adapter.helpers.exceptions import RejectMessageError


class TestCreateOruMessage:
    @pytest.fixture
    def patient_record_uuid(self) -> str:
        return str(uuid.uuid4())

    @pytest.fixture
    def mock_patient_get(
        self, requests_mock: Mocker, patient_uuid: str, patient_record_uuid: str
    ) -> Mock:
        return requests_mock.get(
            f"http://dhos-services/dhos/v1/patient/record/{patient_record_uuid}",
            json={"uuid": patient_uuid},
        )

    @pytest.fixture
    def mock_clinician_get(self, requests_mock: Mocker, clinician_uuid: str) -> Mock:
        return requests_mock.get(
            f"http://dhos-users/dhos/v1/clinician/{clinician_uuid}",
            json={"uuid": clinician_uuid},
        )

    @pytest.fixture
    def mock_location_get(self, requests_mock: Mocker, location_uuid: str) -> Mock:
        return requests_mock.get(
            f"http://dhos-locations/dhos/v1/location/{location_uuid}",
            json={"uuid": location_uuid, "ods_code": "ODS-CODE"},
        )

    @pytest.fixture
    def mock_create_oru_message(self, requests_mock: Mocker) -> Mock:
        return requests_mock.post(
            "http://dhos-connector/dhos/v1/oru_message", status_code=204
        )

    @pytest.fixture
    def clinician(
        self,
        location_uuid: str,
        send_product: str,
        clinician_uuid: str,
        system_user: str,
    ) -> Dict:
        return {
            "job_title": "somejob",
            "send_entry_identifier": None,
            "nhs_smartcard_number": "211214",
            "email_address": "jane.deer@test.com",
            "locations": [location_uuid],
            "bookmarks": [],
            "bookmarked_patients": [],
            "terms_agreement": None,
            "login_active": True,
            "groups": ["GDMClinician"],
            "products": [send_product],
            "can_edit_ews": False,
            "uuid": clinician_uuid,
            "created": "2019-02-04T12:32:18.333Z",
            "created_by": system_user,
            "modified": "2019-02-04T12:32:18.334Z",
            "modified_by": system_user,
            "first_name": "Jane",
            "last_name": "Deer",
            "phone_number": "07654123123",
        }

    @pytest.fixture
    def process_observation_set_message(
        self,
        encounter_uuid: str,
        patient_record_uuid: str,
        location_uuid: str,
        clinician_uuid: str,
    ) -> Dict:
        return {
            "actions": [
                {
                    "name": "process_observation_set",
                    "data": {
                        "encounter": {
                            "patient_record_uuid": patient_record_uuid,
                            "location_uuid": location_uuid,
                        },
                        "observation_set": {
                            "created": "2019-01-31T09:47:27.123Z",
                            "created_by": clinician_uuid,
                            "encounter_id": encounter_uuid,
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
                            "uuid": "observation_set_uuid",
                        },
                    },
                }
            ]
        }

    def test_process_success(
        self,
        mock_patient_get: Mock,
        mock_clinician_get: Mock,
        mock_location_get: Mock,
        mock_create_oru_message: Mock,
        process_observation_set_message: Dict,
        patient_uuid: str,
        patient_record_uuid: str,
        clinician_uuid: str,
        location_uuid: str,
    ) -> None:
        # Arrange
        message_body = json.dumps(process_observation_set_message)
        expected_oru_message_body = process_observation_set_message
        expected_oru_message_body["actions"][0]["data"]["patient"] = {
            "uuid": patient_uuid
        }
        expected_oru_message_body["actions"][0]["data"]["clinician"] = {
            "uuid": clinician_uuid
        }
        expected_oru_message_body["actions"][0]["data"]["encounter"][
            "location_ods_code"
        ] = "ODS-CODE"

        # Act
        create_oru_message.process(body=message_body)

        # Assert
        assert mock_patient_get.call_count == 1
        assert patient_record_uuid in mock_patient_get.last_request.url
        assert mock_clinician_get.call_count == 1
        assert clinician_uuid in mock_clinician_get.last_request.url
        assert mock_location_get.call_count == 1
        assert location_uuid in mock_location_get.last_request.url
        assert mock_create_oru_message.call_count == 1
        assert mock_create_oru_message.last_request.json() == expected_oru_message_body

    @pytest.mark.parametrize(
        "status_code,expected_success", [(404, True), (400, False)]
    )
    def test_process_clinician_get_failure(
        self,
        requests_mock: Mocker,
        mock_patient_get: Mock,
        mock_location_get: Mock,
        mock_create_oru_message: Mock,
        process_observation_set_message: Dict,
        clinician_uuid: str,
        status_code: int,
        expected_success: bool,
    ) -> None:
        # Arrange
        requests_mock.get(
            f"http://dhos-users/dhos/v1/clinician/{clinician_uuid}",
            status_code=status_code,
        )
        message_body = json.dumps(process_observation_set_message)

        if expected_success:
            create_oru_message.process(body=message_body)
            assert mock_create_oru_message.call_count == 1
        else:
            with pytest.raises(RejectMessageError):
                create_oru_message.process(body=message_body)

    @pytest.mark.parametrize(
        "message,error",
        [
            ("not json!", "Couldn't load message body"),
            ({}, "Failed to validate message body"),
            (
                {"actions": [{"name": "process_observation_set"}]},
                "Failed to validate message body",
            ),
            (
                {
                    "actions": [
                        {"name": "process_observation_set", "data": {"encounter": {}}}
                    ]
                },
                "Failed to validate observation set action",
            ),
            (
                {"actions": [{"name": "not_a_process_message", "data": {}}]},
                "No action 'process_observation_set' present in message",
            ),
        ],
    )
    def test_process_invalid_message(
        self, caplog: LogCaptureFixture, message: str, error: str
    ) -> None:
        if not isinstance(message, str):
            message = json.dumps(message)

        with pytest.raises(RejectMessageError):
            create_oru_message.process(message)

        assert error in caplog.text
