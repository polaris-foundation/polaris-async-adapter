import json
from typing import Dict

import pytest
from _pytest.logging import LogCaptureFixture
from mock import Mock
from requests_mock import Mocker

from dhos_async_adapter.callbacks import check_orphaned_observations
from dhos_async_adapter.helpers.exceptions import RejectMessageError


class TestCheckOrphanedObservations:
    @pytest.fixture
    def mock_encounter_get(
        self, requests_mock: Mocker, encounter_uuid: str, patient_record_uuid: str
    ) -> Mock:
        encounter = {
            "uuid": encounter_uuid,
            "location_uuid": "location_uuid",
            "dh_product": [{"uuid": "dh_product_uuid"}],
            "patient_record_uuid": patient_record_uuid,
            "encounter_type": "INPATIENT",
            "admitted_at": "2020-01-01T00:00:00.000Z",
            "score_system": "news2",
        }
        return requests_mock.get(
            f"http://dhos-encounters/dhos/v1/encounter/{encounter_uuid}",
            json=encounter,
        )

    @pytest.fixture
    def mock_observations_get(self, requests_mock: Mocker, encounter_uuid: str) -> Mock:
        return requests_mock.get(
            f"http://dhos-observations/dhos/v2/observation_set?encounter_id={encounter_uuid}",
            json=[],
        )

    @pytest.fixture
    def check_orphaned_observations_message(
        self, encounter_uuid: str, patient_uuid: str, connector_message_id: str
    ) -> Dict:
        return {
            "dhos_connector_message_uuid": connector_message_id,
            "actions": [
                {
                    "name": "check_for_orphaned_observations",
                    "data": {
                        "encounter_uuid": encounter_uuid,
                        "patient_uuid": patient_uuid,
                    },
                },
                {"name": "some_other_action", "data": {"key": "value"}},
                {"name": "some_third_action", "data": {"another_key": "another_value"}},
            ],
        }

    def test_process_success_none(
        self,
        mock_observations_get: Mock,
        mock_hl7_message_patch: Mock,
        check_orphaned_observations_message: Dict,
    ) -> None:
        """
        Tests that when a check_for_orphaned_observations message is processed, and
        the deleted encounter has no observation sets, the message is updated in
        Connector API
        """
        # Arrange
        message_body = json.dumps(check_orphaned_observations_message)

        # Act
        check_orphaned_observations.process(message_body)

        # Assert
        assert mock_observations_get.call_count == 1
        assert mock_hl7_message_patch.call_count == 1

    def test_process_success_lots(
        self,
        requests_mock: Mocker,
        mock_encounter_get: Mock,
        mock_encounter_post: Mock,
        mock_encounter_patch: Mock,
        mock_hl7_message_patch: Mock,
        check_orphaned_observations_message: Dict,
        encounter_uuid: str,
    ) -> None:
        """
        Tests that when a check_for_orphaned_observations message is processed, and
        the deleted encounter has observation sets, the encounter to be merged is fetched,
        a new local encounter created, the original encounter merged into it, and the
        message is updated in Connector API.
        """
        # Arrange
        mock_observations_get = requests_mock.get(
            f"http://dhos-observations/dhos/v2/observation_set?encounter_id={encounter_uuid}",
            json=[
                {"uuid": "obs_set_1"},
                {"uuid": "obs_set_2"},
                {"uuid": "obs_set_3"},
            ],
        )
        message_body = json.dumps(check_orphaned_observations_message)

        # Act
        check_orphaned_observations.process(message_body)

        # Assert
        assert mock_observations_get.call_count == 1
        assert mock_encounter_get.call_count == 1
        assert mock_encounter_post.call_count == 1
        assert mock_encounter_patch.call_count == 1
        assert mock_encounter_patch.last_request.url.endswith(encounter_uuid)
        assert mock_hl7_message_patch.call_count == 1

    def test_process_abort_if_already_merged(
        self,
        requests_mock: Mocker,
        mock_encounter_post: Mock,
        mock_hl7_message_patch: Mock,
        check_orphaned_observations_message: Dict,
        encounter_uuid: str,
        caplog: LogCaptureFixture,
    ) -> None:
        """
        Tests that if the encounter to be merged is already a child of an existing encounter,
        the merge process is aborted but the message is still updated in Connector API.
        """
        # Arrange
        mock_observations_get = requests_mock.get(
            f"http://dhos-observations/dhos/v2/observation_set?encounter_id={encounter_uuid}",
            json=[
                {"uuid": "obs_set_1"},
                {"uuid": "obs_set_2"},
                {"uuid": "obs_set_3"},
            ],
        )
        mock_encounter_get = requests_mock.get(
            f"http://dhos-encounters/dhos/v1/encounter/{encounter_uuid}",
            json={"uuid": encounter_uuid, "child_of": "some_existing_encounter_uuid"},
        )
        message_body = json.dumps(check_orphaned_observations_message)

        # Act
        check_orphaned_observations.process(message_body)

        # Assert
        assert mock_observations_get.call_count == 1
        assert mock_encounter_get.call_count == 1
        assert mock_encounter_post.call_count == 0
        assert mock_hl7_message_patch.call_count == 1
        assert "Aborting merge" in caplog.text

    @pytest.mark.parametrize(
        "invalid_body",
        [
            {
                # No action with the right name
                "dhos_connector_message_uuid": "some_uuid",
                "actions": [
                    {"name": "some_other_action", "data": {"key": "value"}},
                    {
                        "name": "some_third_action",
                        "data": {"another_key": "another_value"},
                    },
                ],
            },
            {
                # Data is of the wrong type
                "dhos_connector_message_uuid": "some_uuid",
                "actions": [
                    {
                        "name": "check_for_orphaned_observations",
                        "data": {"key": "value"},
                    },
                ],
            },
            {
                # Data is missing
                "dhos_connector_message_uuid": "some_uuid",
                "actions": [
                    {"name": "check_for_orphaned_observations"},
                ],
            },
            {
                # Actions are missing
                "dhos_connector_message_uuid": "some_uuid"
            },
        ],
    )
    def test_process_invalid_body(
        self, mock_observations_get: Mock, invalid_body: Dict
    ) -> None:
        # Arrange
        message_body = json.dumps(invalid_body)

        # Act
        with pytest.raises(RejectMessageError):
            check_orphaned_observations.process(message_body)

        # Assert
        assert mock_observations_get.call_count == 0

    def test_process_bad_response(
        self,
        requests_mock: Mocker,
        check_orphaned_observations_message: Dict,
        encounter_uuid: str,
    ) -> None:
        # Arrange
        message_body = json.dumps(check_orphaned_observations_message)
        mock_observations_get: Mock = requests_mock.get(
            f"http://dhos-observations/dhos/v2/observation_set?encounter_id={encounter_uuid}",
            status_code=400,
        )

        # Act
        with pytest.raises(RejectMessageError):
            check_orphaned_observations.process(message_body)

        # Assert
        assert mock_observations_get.call_count == 1
