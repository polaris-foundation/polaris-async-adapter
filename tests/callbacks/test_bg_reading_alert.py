import json
from typing import Dict

import pytest
from mock import Mock
from requests_mock import Mocker

from dhos_async_adapter.callbacks import bg_reading_alert
from dhos_async_adapter.callbacks.bg_reading_alert import AlertType
from dhos_async_adapter.helpers.exceptions import RejectMessageError


@pytest.mark.usefixtures("mock_get_request_headers")
class TestBgReadingAlert:
    @pytest.fixture
    def mock_patient_get(
        self, requests_mock: Mocker, patient_uuid: str, location_uuid: str
    ) -> Mock:
        return requests_mock.get(
            f"http://dhos-services/dhos/v1/patient/{patient_uuid}",
            json={
                "uuid": patient_uuid,
                "first_name": "Laura",
                "locations": [location_uuid],
            },
        )

    @pytest.fixture
    def mock_messages_post(self, requests_mock: Mocker, clinician_uuid: str) -> Mock:
        return requests_mock.post("http://dhos-messages/dhos/v2/message")

    @pytest.fixture
    def alert_message(self, patient_uuid: str) -> Dict:
        return {
            "patient_uuid": patient_uuid,
            "alert_type": AlertType.PERCENTAGES_RED.value,
        }

    def test_process_success(
        self,
        mock_patient_get: Mock,
        mock_messages_post: Mock,
        alert_message: Dict,
        patient_uuid: str,
        location_uuid: str,
    ) -> None:
        # Arrange
        message_body = json.dumps(alert_message)
        expected_message_body = {
            "sender": patient_uuid,
            "sender_type": "patient",
            "receiver": location_uuid,
            "receiver_type": "location",
            "message_type": {"value": 7},
            "content": "At least 30% of readings posted by Laura in the last 7 days have been out of threshold.",
        }

        # Act
        bg_reading_alert.process(message_body)

        # Assert
        assert mock_patient_get.call_count == 1
        assert patient_uuid in mock_patient_get.last_request.url
        assert mock_messages_post.call_count == 1
        assert mock_messages_post.last_request.json() == expected_message_body

    def test_process_abort_non_gdm(
        self,
        requests_mock: Mocker,
        mock_messages_post: Mock,
        alert_message: Dict,
        patient_uuid: str,
    ) -> None:
        # Arrange
        message_body = json.dumps(alert_message)
        mock_patient_get = requests_mock.get(
            f"http://dhos-services/dhos/v1/patient/{patient_uuid}",
            status_code=404,
        )

        # Act
        bg_reading_alert.process(message_body)

        # Assert
        assert mock_patient_get.call_count == 1
        assert patient_uuid in mock_patient_get.last_request.url
        assert mock_messages_post.call_count == 0

    def test_process_invalid_body(self, mock_patient_get: Mock) -> None:
        # Arrange
        message_body = json.dumps(
            {"patient_uuid": "any-patient-uuid", "alert_type": "NOT-KNOWN-ALERT-TYPE"}
        )

        # Act
        with pytest.raises(RejectMessageError):
            bg_reading_alert.process(message_body)

        # Assert
        assert mock_patient_get.call_count == 0

    def test_process_grey_alert(
        self,
        mock_patient_get: Mock,
        mock_messages_post: Mock,
    ) -> None:
        # Arrange
        message_body = json.dumps(
            {
                "patient_uuid": "any-patient-uuid",
                "alert_type": AlertType.ACTIVITY_GREY.value,
            }
        )

        # Act
        bg_reading_alert.process(message_body)

        # Assert
        assert mock_messages_post.call_count == 0
        assert mock_patient_get.call_count == 0

    @pytest.mark.parametrize(
        "alert_type,expected_value,expected_text",
        [
            (
                AlertType.COUNTS_RED.value,
                7,
                "Laura has posted at least 3 consecutive out of threshold readings for this meal time.",
            ),
            (
                AlertType.COUNTS_AMBER.value,
                8,
                "Laura has posted at least 2 out of threshold readings within the past 2 days where readings were taken",
            ),
            (
                AlertType.PERCENTAGES_RED.value,
                7,
                f"At least 30% of readings posted by Laura in the last 7 days have been out of threshold.",
            ),
            (
                AlertType.PERCENTAGES_AMBER.value,
                8,
                f"Between 10% and 30% of readings posted by Laura in the last 7 days have been out of threshold.",
            ),
        ],
    )
    def test_process_known_alert_types(
        self,
        mock_patient_get: Mock,
        mock_messages_post: Mock,
        patient_uuid: str,
        alert_type: str,
        expected_value: int,
        expected_text: str,
    ) -> None:
        # Arrange
        alert_message = {"patient_uuid": patient_uuid, "alert_type": alert_type}
        message_body = json.dumps(alert_message)

        # Act
        bg_reading_alert.process(message_body)

        # Assert
        assert mock_patient_get.call_count == 1
        message_request_body = mock_messages_post.last_request.json()
        assert message_request_body["message_type"]["value"] == expected_value
        assert message_request_body["content"] == expected_text

    def test_impossible_scenario_for_coverage(self) -> None:
        # The worst kind of coverage chasing.
        with pytest.raises(RejectMessageError):
            bg_reading_alert._extract_alert_message_details(
                AlertType.ACTIVITY_GREY, "anything"
            )
