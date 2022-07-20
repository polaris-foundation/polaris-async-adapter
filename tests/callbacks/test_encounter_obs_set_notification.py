import json
from typing import Dict

import pytest
from mock import Mock
from requests_mock import Mocker

from dhos_async_adapter.callbacks import encounter_obs_set_notification


class TestEncounterObsSetNotification:
    @pytest.fixture
    def mock_encounter_get(self, requests_mock: Mocker, encounter_uuid: str) -> Mock:
        return requests_mock.get(
            f"http://dhos-encounters/dhos/v1/encounter/{encounter_uuid}",
            json={"uuid": encounter_uuid},
        )

    @pytest.fixture
    def process_observation_set_message(self, encounter_uuid: str) -> Dict:
        return {
            "actions": [
                {
                    "name": "process_observation_set",
                    "data": {
                        "observation_set": {
                            "created": "2019-01-31T09:47:27.123Z",
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
                        }
                    },
                }
            ]
        }

    def test_process_success(
        self,
        mock_encounter_get: Mock,
        mock_publish: Mock,
        process_observation_set_message: Dict,
        encounter_uuid: str,
    ) -> None:
        # Arrange
        message_body = json.dumps(process_observation_set_message)
        expected_published_message_body = process_observation_set_message
        expected_published_message_body["actions"][0]["data"]["encounter"] = {
            "uuid": encounter_uuid
        }

        # Act
        encounter_obs_set_notification.process(body=message_body)

        # Assert
        assert mock_encounter_get.call_count == 1
        assert mock_publish.call_count == 1
        mock_publish.assert_called_with(
            routing_key="dhos.DM000005", body=expected_published_message_body
        )
