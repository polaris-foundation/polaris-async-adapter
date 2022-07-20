import json
import re
from typing import Dict

import pytest
from marshmallow import ValidationError
from mock import Mock
from requests_mock import Mocker

from dhos_async_adapter.callbacks import check_orphaned_observations, encounter_update
from dhos_async_adapter.helpers.exceptions import RejectMessageError


@pytest.mark.usefixtures("mock_publish")
class TestEncounterUpdate:
    @pytest.fixture
    def num_existing_open_local_encounters(self) -> int:
        return 0

    @pytest.fixture
    def num_existing_epr_encounters(self) -> int:
        return 0

    @pytest.fixture
    def mock_open_local_encounters_get(
        self,
        requests_mock: Mocker,
        patient_uuid: str,
        num_existing_open_local_encounters: int,
    ) -> Mock:
        matcher = re.compile(
            r"^http://dhos-encounters/dhos/v2/encounter\?patient_id="
            + patient_uuid
            + r"&open_as_of="
        )
        json_body = [
            {
                "uuid": f"local_encounter_uuid_{i+1}",
                "created": "2018-01-01T00:00:00.000Z",
                "modified": "2018-01-01T00:00:00.000Z",
                "epr_encounter_id": "",
                "encounter_type": "INPATIENT",
                "admitted_at": "2017-09-23T08:29:19.123+00:00",
                "discharged_at": "2017-09-23T08:29:19.123+00:00",
                "location_uuid": "2c4f1d24-2952-4d4e-b1d1-3637e33cc161",
            }
            for i in range(num_existing_open_local_encounters)
        ]
        return requests_mock.get(matcher, json=json_body)

    @pytest.fixture
    def mock_epr_encounters_get(
        self,
        requests_mock: Mocker,
        patient_uuid: str,
        epr_encounter_id: str,
        num_existing_epr_encounters: int,
    ) -> Mock:
        matcher = re.compile(
            r"^http://dhos-encounters/dhos/v2/encounter\?patient_id="
            + patient_uuid
            + r"&epr_encounter_id="
        )
        json_body = [
            {
                "uuid": f"epr_encounter_uuid_{i+1}",
                "created": "2018-01-02T00:00:00.000Z",
                "modified": "2018-01-02T00:00:00.000Z",
                "epr_encounter_id": epr_encounter_id,
                "encounter_type": "INPATIENT",
                "admitted_at": "2017-09-23T08:29:19.123+00:00",
                "discharged_at": "2017-09-23T08:29:19.123+00:00",
                "location_uuid": "2c4f1d24-2952-4d4e-b1d1-3637e33cc161",
            }
            for i in range(num_existing_epr_encounters)
        ]
        return requests_mock.get(matcher, json=json_body)

    @pytest.fixture
    def process_encounter_message(
        self, patient_uuid: str, epr_encounter_id: str, connector_message_id: str
    ) -> Dict:
        return {
            "dhos_connector_message_uuid": connector_message_id,
            "actions": [
                {
                    "name": "process_patient",
                    "data": {
                        "first_name": "STEPHEN",
                        "last_name": "ZZZEDUCATION",
                        "sex_sct": "248153007",
                        "nhs_number": "4902374218",
                        "mrn": "1218357",
                        "date_of_birth": "1982-11-03",
                    },
                },
                {
                    "name": "process_location",
                    "data": {
                        "location": {
                            "epr_ward_code": "NOC-Ward B",
                            "epr_bay_code": "Day Room",
                            "epr_bed_code": "Chair 6",
                        }
                    },
                },
                {
                    "name": "process_encounter",
                    "data": {
                        "epr_encounter_id": epr_encounter_id,
                        "location": {
                            "epr_ward_code": "NOC-Ward B",
                            "epr_bay_code": "Day Room",
                            "epr_bed_code": "Chair 6",
                        },
                        "encounter_type": "INPATIENT",
                        "admitted_at": "2020-01-01T00:00:00.000Z",
                        "admission_cancelled": False,
                        "transfer_cancelled": False,
                        "discharge_cancelled": False,
                        "encounter_moved": False,
                        "patient_deceased": False,
                        "patient_uuid": patient_uuid,
                        "patient_record_uuid": "dd5e1de0-d52a-40d7-9b1d-3e011afb48c6",
                        "dh_product_uuid": "afb3076c-3159-4767-9d08-cd83a52a8638",
                        "location_uuid": "ffff32f26-98c6-4f8f-b3e7-1d851d3f0909",
                        "score_system_default_for_location": "news2",
                    },
                },
            ],
        }

    def test_process_no_existing(
        self,
        mock_open_local_encounters_get: Mock,
        mock_epr_encounters_get: Mock,
        mock_encounter_post: Mock,
        mock_hl7_message_patch: Mock,
        process_encounter_message: Dict,
        connector_message_id: str,
        num_existing_open_local_encounters: int,
        num_existing_epr_encounters: int,
    ) -> None:
        """
        Tests that when there are no existing encounters for the patient, a new one is
        created and the message is updated in Connector API.
        """
        # Arrange
        message_body = json.dumps(process_encounter_message)

        # Act
        encounter_update.process(message_body)

        # Assert
        assert mock_open_local_encounters_get.call_count == 1
        assert mock_epr_encounters_get.call_count == 1
        assert mock_encounter_post.call_count == 1
        actual_encounter: Dict = mock_encounter_post.last_request.json()
        for field in [
            "location_uuid",
            "dh_product_uuid",
            "patient_record_uuid",
            "epr_encounter_id",
            "encounter_type",
            "admitted_at",
        ]:
            assert (
                actual_encounter[field]
                == process_encounter_message["actions"][2]["data"][field]
            )
        # Check score system has defaulted correctly
        assert (
            actual_encounter["score_system"]
            == process_encounter_message["actions"][2]["data"][
                "score_system_default_for_location"
            ]
        )

        assert mock_hl7_message_patch.call_count == 1

    @pytest.mark.parametrize("num_existing_open_local_encounters", [1])
    def test_process_existing_local(
        self,
        mock_open_local_encounters_get: Mock,
        mock_epr_encounters_get: Mock,
        mock_encounter_patch: Mock,
        mock_hl7_message_patch: Mock,
        process_encounter_message: Dict,
        epr_encounter_id: str,
        num_existing_open_local_encounters: int,
    ) -> None:
        """
        Tests that when there is an open local encounters for the patient, it is made
        into an EPR encounter and the message is updated in Connector API.
        """
        # Arrange
        message_body = json.dumps(process_encounter_message)

        # Act
        encounter_update.process(message_body)

        # Assert
        assert mock_encounter_patch.last_request.url.endswith("local_encounter_uuid_1")
        actual_encounter_update: Dict = mock_encounter_patch.last_request.json()
        assert actual_encounter_update["epr_encounter_id"] == epr_encounter_id
        assert actual_encounter_update["admitted_at"] == "2020-01-01T00:00:00.000Z"
        assert mock_hl7_message_patch.call_count == 1

    @pytest.mark.parametrize("num_existing_epr_encounters", [1])
    def test_process_existing_epr(
        self,
        mock_open_local_encounters_get: Mock,
        mock_epr_encounters_get: Mock,
        mock_encounter_patch: Mock,
        mock_hl7_message_patch: Mock,
        process_encounter_message: Dict,
        num_existing_epr_encounters: int,
    ) -> None:
        """
        Tests that when there is a matching EPR encounter for the patient, it is updated
        and the message is updated in Connector API.
        """
        # Arrange
        message_body = json.dumps(process_encounter_message)

        # Act
        encounter_update.process(message_body)

        # Assert
        assert mock_encounter_patch.last_request.url.endswith("epr_encounter_uuid_1")
        actual_encounter_update: Dict = mock_encounter_patch.last_request.json()
        assert actual_encounter_update["admitted_at"] == "2020-01-01T00:00:00.000Z"
        assert mock_hl7_message_patch.call_count == 1

    @pytest.mark.parametrize(
        ["num_existing_open_local_encounters", "num_existing_epr_encounters"], [(4, 4)]
    )
    def test_process_existing_multiple(
        self,
        mock_open_local_encounters_get: Mock,
        mock_epr_encounters_get: Mock,
        mock_encounter_patch: Mock,
        mock_hl7_message_patch: Mock,
        process_encounter_message: Dict,
        num_existing_open_local_encounters: int,
        num_existing_epr_encounters: int,
    ) -> None:
        """
        Tests that when there are multiple matching EPR encounters for the patient, one
        is updated, the others are merged and the message is updated in Connector API.
        """
        # Arrange
        message_body = json.dumps(process_encounter_message)

        # Act
        encounter_update.process(message_body)

        # Assert
        assert mock_encounter_patch.call_count == 8
        assert mock_encounter_patch.request_history[0].url.endswith(
            "epr_encounter_uuid_1"
        )
        actual_encounter_update: Dict = mock_encounter_patch.request_history[0].json()
        assert actual_encounter_update["admitted_at"] == "2020-01-01T00:00:00.000Z"
        for i in range(1, 8):
            assert (
                mock_encounter_patch.request_history[i]
                .json()
                .get("child_of_encounter_uuid")
                == "epr_encounter_uuid_1"
            )
        assert mock_hl7_message_patch.call_count == 1

    def test_process_deceased(
        self,
        mock_open_local_encounters_get: Mock,
        mock_epr_encounters_get: Mock,
        mock_encounter_post: Mock,
        mock_encounter_patch: Mock,
        mock_hl7_message_patch: Mock,
        process_encounter_message: Dict,
        num_existing_open_local_encounters: int,
        num_existing_epr_encounters: int,
    ) -> None:
        """
        Tests that when a patient is deceased and has an open encounter, the encounter
        is marked as discharged.
        """
        # Arrange
        process_encounter_message["actions"][2]["data"]["patient_deceased"] = True
        message_body = json.dumps(process_encounter_message)

        # Act
        encounter_update.process(message_body)

        # Assert
        assert mock_encounter_post.call_count == 1
        assert mock_encounter_patch.call_count == 1
        assert mock_encounter_patch.last_request.url.endswith("new_encounter_uuid")
        assert mock_encounter_patch.last_request.json()["discharged_at"] is not None
        assert mock_hl7_message_patch.call_count == 1

    def test_process_admission_cancelled(
        self,
        mock_open_local_encounters_get: Mock,
        mock_epr_encounters_get: Mock,
        mock_encounter_post: Mock,
        mock_encounter_patch: Mock,
        mock_publish: Mock,
        process_encounter_message: Dict,
        num_existing_open_local_encounters: int,
        num_existing_epr_encounters: int,
        connector_message_id: str,
        patient_uuid: str,
    ) -> None:
        """
        Tests that when an encounter's admission is cancelled, it is marked as deleted and a
        "check for orphaned observations" message (dhos.DM000002) is published.
        """
        # Arrange
        process_encounter_message["actions"][2]["data"]["admission_cancelled"] = True
        message_body = json.dumps(process_encounter_message)
        expected_published_message_body = {
            "dhos_connector_message_uuid": connector_message_id,
            "actions": [
                {
                    "name": "check_for_orphaned_observations",
                    "data": {
                        "encounter_uuid": "new_encounter_uuid",
                        "patient_uuid": patient_uuid,
                    },
                }
            ],
        }

        # Act
        encounter_update.process(message_body)

        # Assert
        assert mock_encounter_post.call_count == 1
        assert mock_encounter_post.last_request.json()["deleted_at"] is not None
        assert mock_publish.call_count == 1
        mock_publish.assert_called_with(
            routing_key=check_orphaned_observations.ROUTING_KEY,
            body=expected_published_message_body,
        )

    def test_process_discharge_cancelled(
        self,
        mock_open_local_encounters_get: Mock,
        mock_epr_encounters_get: Mock,
        mock_encounter_post: Mock,
        mock_encounter_patch: Mock,
        mock_hl7_message_patch: Mock,
        process_encounter_message: Dict,
        num_existing_open_local_encounters: int,
        num_existing_epr_encounters: int,
    ) -> None:
        """
        Tests that when an encounter's discharge is cancelled, the encounter
        is marked as not discharged.
        """
        # Arrange
        process_encounter_message["actions"][2]["data"]["discharge_cancelled"] = True
        process_encounter_message["actions"][2]["data"][
            "discharged_at"
        ] = "2020-01-01T00:00:00.000Z"
        message_body = json.dumps(process_encounter_message)

        # Act
        encounter_update.process(message_body)

        # Assert
        assert mock_encounter_post.call_count == 1
        assert mock_encounter_post.last_request.json()["discharged_at"] is None
        assert mock_hl7_message_patch.call_count == 1

    def test_process_merge_patient_encounters(
        self,
        requests_mock: Mocker,
        mock_open_local_encounters_get: Mock,
        mock_epr_encounters_get: Mock,
        mock_encounter_post: Mock,
        mock_encounter_patch: Mock,
        mock_hl7_message_patch: Mock,
        process_encounter_message: Dict,
        num_existing_open_local_encounters: int,
        num_existing_epr_encounters: int,
        connector_message_id: str,
    ) -> None:
        """
        Tests that when an encounter is marked as requiring a patient merge,
        the merge request is made correctly.
        """
        # Arrange
        process_encounter_message["actions"][2]["data"][
            "merge_patient_record_uuid"
        ] = "merge_patient_record_uuid"
        message_body = json.dumps(process_encounter_message)
        mock_merge: Mock = requests_mock.post(
            "http://dhos-encounters/dhos/v1/encounter/merge"
        )

        # Act
        encounter_update.process(message_body)

        # Assert
        assert mock_encounter_post.call_count == 1
        assert mock_merge.call_count == 1
        assert mock_merge.last_request.json() == {
            "child_record_uuid": "merge_patient_record_uuid",
            "parent_record_uuid": process_encounter_message["actions"][2]["data"][
                "patient_record_uuid"
            ],
            "parent_patient_uuid": process_encounter_message["actions"][2]["data"][
                "patient_uuid"
            ],
            "message_uuid": connector_message_id,
        }
        assert mock_hl7_message_patch.call_count == 1

    def test_process_invalid_body(self, mock_open_local_encounters_get: Mock) -> None:
        # Arrange
        message_body = json.dumps(
            {
                "dhos_connector_message_uuid": "connector_message_id",
                "actions": [{"name": "process_encounter", "data": {"some": "garbage"}}],
            }
        )

        # Act
        with pytest.raises(ValidationError):
            encounter_update.process(message_body)

        # Assert
        assert mock_open_local_encounters_get.call_count == 0

    def test_process_bad_response(
        self,
        requests_mock: Mocker,
        process_encounter_message: Dict,
        patient_uuid: str,
    ) -> None:
        # Arrange
        message_body = json.dumps(process_encounter_message)
        mock_encounters_get: Mock = requests_mock.get(
            f"http://dhos-encounters/dhos/v2/encounter?patient_id={patient_uuid}",
            status_code=400,
        )

        # Act
        with pytest.raises(RejectMessageError):
            encounter_update.process(message_body)

        # Assert
        assert mock_encounters_get.call_count == 1
