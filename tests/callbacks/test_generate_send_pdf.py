import json
from typing import Dict, List

import pytest
from mock import Mock
from pytest_mock import MockFixture
from requests_mock import Mocker

from dhos_async_adapter.callbacks import generate_send_pdf


class TestGenerateSendPdf:
    @pytest.fixture
    def observations(self) -> List[Dict]:
        return [
            {
                "observation_string": None,
                "observation_type": "heart_rate",
                "observation_unit": "bpm",
                "observation_value": None,
                "patient_refused": True,
                "uuid": "c93507d5-e857-48e2-a195-6ee95dff09f5",
            },
            {
                "observation_type": "consciousness_acvpu",
                "observation_unit": None,
                "observation_value": None,
                "patient_refused": False,
                "uuid": "c93507d5-e857-48e2-a195-6ee95dff09f6",
            },
            {
                "observation_type": "spo2",
                "observation_unit": None,
                "observation_value": None,
                "patient_refused": False,
                "uuid": "c93507d5-e857-48e2-a195-6ee95dff09f7",
            },
        ]

    @pytest.fixture
    def encounter_response(
        self, encounter_uuid: str, patient_record_uuid: str, location_uuid: str
    ) -> Dict:
        return {
            "uuid": encounter_uuid,
            "patient_record_uuid": patient_record_uuid,
            "location_uuid": location_uuid,
            "score_system_history": [
                {"uuid": "h1", "created_by": "clinician_1"},
                {"uuid": "h2", "created_by": None},
                {"uuid": "h3", "created_by": "some_unknown_uuid"},
            ],
        }

    @pytest.fixture
    def patient_response(self, patient_uuid: str) -> Dict:
        return {"uuid": patient_uuid}

    @pytest.fixture
    def location_response(self, location_uuid: str) -> Dict:
        return {
            "uuid": location_uuid,
            "display_name": "a ward",
            "parents": [{"display_name": "A hospital"}],
        }

    @pytest.fixture
    def clinicians_response(self) -> Dict:
        return {
            "clinician_1": {
                "uuid": "clinician_1",
                "first_name": "Jane",
                "last_name": "Bloggs",
            }
        }

    @pytest.fixture
    def obs_sets_by_encounter_response(self, observations: List[Dict]) -> List:
        return [
            {
                "uuid": "obs_set_1",
                "created_by": "clinician_1",
                "monitoring_instruction": "low_monitoring",
                "observations": observations,
                "record_time": "2019-08-27T17:00:00.000Z",
                "time_next_obs_set_due": "2019-08-27T18:00:00.000Z",
            },
            {
                "uuid": "obs_set_2",
                "created_by": "clinician_2",
                "monitoring_instruction": "low_monitoring",
                "observations": observations,
                "record_time": "2019-08-27T18:00:00.000Z",
                "time_next_obs_set_due": "2019-08-27T19:00:00.000Z",
            },
            {
                "uuid": "obs_set_3",
                "created_by": "clinician_3",
                "monitoring_instruction": "low_monitoring",
                "observations": observations,
                "record_time": "2019-08-27T19:00:00.000Z",
                "time_next_obs_set_due": "2019-08-27T20:00:00.000Z",
            },
        ]

    @pytest.fixture
    def expected_aggregated_data(
        self,
        encounter_uuid: str,
        patient_uuid: str,
        patient_record_uuid: str,
        location_uuid: str,
    ) -> Dict:
        return {
            "aggregation_time": "2019-01-01T12:00:00.000+00:00",
            "encounter": {
                "uuid": encounter_uuid,
                "patient_record_uuid": patient_record_uuid,
                "location_uuid": location_uuid,
                "score_system_history": [
                    {
                        "uuid": "h1",
                        "created_by": "clinician_1",
                        "changed_by": {
                            "uuid": "clinician_1",
                            "first_name": "Jane",
                            "last_name": "Bloggs",
                        },
                    },
                    {
                        "uuid": "h2",
                        "created_by": None,
                        "changed_by": {"uuid": None, "first_name": "", "last_name": ""},
                    },
                    {
                        "uuid": "h3",
                        "created_by": "some_unknown_uuid",
                        "changed_by": {
                            "uuid": "some_unknown_uuid",
                            "first_name": "",
                            "last_name": "",
                        },
                    },
                ],
            },
            "patient": {"uuid": patient_uuid},
            "location": {
                "uuid": location_uuid,
                "display_name": "a ward",
                "parents": [{"display_name": "A hospital"}],
            },
            "observation_sets": [
                {
                    "uuid": "obs_set_1",
                    "created_by": {
                        "uuid": "clinician_1",
                        "first_name": "Jane",
                        "last_name": "Bloggs",
                    },
                    "monitoring_instruction": "low_monitoring",
                    "observations": [
                        {
                            "observation_string": None,
                            "observation_type": "heart_rate",
                            "observation_unit": "bpm",
                            "observation_value": None,
                            "patient_refused": True,
                            "uuid": "c93507d5-e857-48e2-a195-6ee95dff09f5",
                        },
                        {
                            "observation_type": "consciousness_acvpu",
                            "observation_unit": None,
                            "observation_value": None,
                            "patient_refused": False,
                            "uuid": "c93507d5-e857-48e2-a195-6ee95dff09f6",
                        },
                        {
                            "observation_type": "spo2",
                            "observation_unit": None,
                            "observation_value": None,
                            "patient_refused": False,
                            "uuid": "c93507d5-e857-48e2-a195-6ee95dff09f7",
                        },
                    ],
                    "record_time": "2019-08-27T17:00:00.000Z",
                    "time_next_obs_set_due": "2019-08-27T18:00:00.000Z",
                },
                {
                    "uuid": "obs_set_2",
                    "created_by": {
                        "uuid": "clinician_2",
                        "first_name": "",
                        "last_name": "",
                    },
                    "monitoring_instruction": "low_monitoring",
                    "observations": [
                        {
                            "observation_string": None,
                            "observation_type": "heart_rate",
                            "observation_unit": "bpm",
                            "observation_value": None,
                            "patient_refused": True,
                            "uuid": "c93507d5-e857-48e2-a195-6ee95dff09f5",
                        },
                        {
                            "observation_type": "consciousness_acvpu",
                            "observation_unit": None,
                            "observation_value": None,
                            "patient_refused": False,
                            "uuid": "c93507d5-e857-48e2-a195-6ee95dff09f6",
                        },
                        {
                            "observation_type": "spo2",
                            "observation_unit": None,
                            "observation_value": None,
                            "patient_refused": False,
                            "uuid": "c93507d5-e857-48e2-a195-6ee95dff09f7",
                        },
                    ],
                    "record_time": "2019-08-27T18:00:00.000Z",
                    "time_next_obs_set_due": "2019-08-27T19:00:00.000Z",
                },
                {
                    "uuid": "obs_set_3",
                    "created_by": {
                        "uuid": "clinician_3",
                        "first_name": "",
                        "last_name": "",
                    },
                    "monitoring_instruction": "low_monitoring",
                    "observations": [
                        {
                            "observation_string": None,
                            "observation_type": "heart_rate",
                            "observation_unit": "bpm",
                            "observation_value": None,
                            "patient_refused": True,
                            "uuid": "c93507d5-e857-48e2-a195-6ee95dff09f5",
                        },
                        {
                            "observation_type": "consciousness_acvpu",
                            "observation_unit": None,
                            "observation_value": None,
                            "patient_refused": False,
                            "uuid": "c93507d5-e857-48e2-a195-6ee95dff09f6",
                        },
                        {
                            "observation_type": "spo2",
                            "observation_unit": None,
                            "observation_value": None,
                            "patient_refused": False,
                            "uuid": "c93507d5-e857-48e2-a195-6ee95dff09f7",
                        },
                    ],
                    "record_time": "2019-08-27T19:00:00.000Z",
                    "time_next_obs_set_due": "2019-08-27T20:00:00.000Z",
                },
            ],
        }

    @pytest.fixture
    def mock_clients(
        self,
        requests_mock: Mocker,
        mocker: MockFixture,
        encounter_response: Dict,
        patient_response: Dict,
        location_response: Dict,
        clinicians_response: Dict[str, Dict],
        obs_sets_by_encounter_response: List[Dict],
        encounter_uuid: str,
        patient_record_uuid: str,
        location_uuid: str,
    ) -> List[Mock]:
        mock_1 = requests_mock.get(
            f"http://dhos-encounters/dhos/v1/encounter/{encounter_uuid}",
            json=encounter_response,
        )
        mock_2 = requests_mock.get(
            f"http://dhos-encounters/dhos/v1/encounter/{encounter_uuid}/children",
            json=[],
        )
        mock_3 = requests_mock.get(
            f"http://dhos-services/dhos/v1/patient/record/{patient_record_uuid}",
            json=patient_response,
        )
        mock_4 = requests_mock.get(
            f"http://dhos-locations/dhos/v1/location/{location_uuid}",
            json=location_response,
        )
        mock_5 = requests_mock.post(
            f"http://dhos-users/dhos/v1/clinician_list?compact=True",
            json=clinicians_response,
        )
        mock_6 = requests_mock.get(
            f"http://dhos-observations/dhos/v2/observation_set?encounter_id={encounter_uuid}",
            json=obs_sets_by_encounter_response,
        )
        return [mock_1, mock_2, mock_3, mock_4, mock_5, mock_6]

    @pytest.fixture
    def mock_create_pdf(self, requests_mock: Mocker, encounter_uuid: str) -> Mock:
        return requests_mock.post(f"http://dhos-pdf/dhos/v1/send_pdf", status_code=201)

    @pytest.fixture
    def aggregate_message(self, encounter_uuid: str) -> Dict:
        return {"encounter_id": encounter_uuid}

    @pytest.mark.freeze_time("2019-01-01 12:00:00")
    def test_process_success(
        self,
        mock_clients: List[Mock],
        mock_create_pdf: Mock,
        aggregate_message: Dict,
        expected_aggregated_data: Dict,
    ) -> None:
        # Arrange
        message_body: str = json.dumps(aggregate_message)

        # Act
        generate_send_pdf.process(message_body)

        # Assert
        for mock_endpoint in mock_clients:
            assert mock_endpoint.call_count == 1
        assert mock_create_pdf.call_count == 1
        assert mock_create_pdf.last_request.json() == expected_aggregated_data

    # def test_process_encounter_request_failure(
    #         self,
    #         mock_clients: List[Mock],
    #         mock_req
    #         aggregate_message: Dict,
    # ) -> None:
    #     # Arrange
    #     mock_encounter_get: Mock = mocker.patch.object(
    #         encounters_api, "get_encounter_by_uuid", return_value=encounter_response
    #     )
    #
    #     message_body: str = json.dumps(aggregate_message)
    #
    #     # Act
    #     generate_send_pdf.process(message_body)
    #
    #     # Assert
    #     for mock_endpoint in mock_clients:
    #         assert mock_endpoint.call_count == 1
    #     assert mock_create_pdf.call_count == 1
    #     assert mock_create_pdf.last_request.json() == expected_aggregated_data
