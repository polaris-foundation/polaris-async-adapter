import json
import uuid
from typing import Dict, Optional

import draymed
import pytest
from _pytest.logging import LogCaptureFixture
from mock import Mock
from pytest_mock import MockFixture
from requests_mock import Mocker

from dhos_async_adapter.callbacks import patient_update
from dhos_async_adapter.clients import services_api
from dhos_async_adapter.helpers.exceptions import RejectMessageError


@pytest.mark.usefixtures("mock_publish")
class TestPatientUpdate:
    @pytest.fixture
    def product_uuid(self) -> str:
        return str(uuid.uuid4())

    @pytest.fixture
    def mock_get_patient_by_identifiers(self, requests_mock: Mocker) -> Mock:
        return requests_mock.get("http://dhos-services/dhos/v1/patient", json=[])

    @pytest.fixture
    def mock_post_patient(
        self,
        requests_mock: Mocker,
        patient_uuid: str,
        patient_record_uuid: str,
        product_uuid: str,
    ) -> Mock:
        return requests_mock.post(
            "http://dhos-services/dhos/v1/patient",
            json={
                "uuid": patient_uuid,
                "dh_products": [{"uuid": product_uuid, "product_name": "SEND"}],
                "record": {"uuid": patient_record_uuid},
            },
        )

    @pytest.fixture
    def mock_patch_patient(
        self,
        requests_mock: Mocker,
        patient_uuid: str,
        patient_record_uuid: str,
        product_uuid: str,
    ) -> Mock:
        return requests_mock.patch(
            f"http://dhos-services/dhos/v1/patient/{patient_uuid}",
            json={
                "uuid": patient_uuid,
                "dh_products": [{"uuid": product_uuid, "product_name": "SEND"}],
                "record": {"uuid": patient_record_uuid},
            },
        )

    @pytest.fixture
    def mock_get_location_by_ods_code(self, requests_mock: Mocker) -> Mock:
        return requests_mock.get(
            "http://dhos-locations/dhos/v1/location/search", json={}
        )

    @pytest.fixture
    def mock_post_location(self, requests_mock: Mocker, location_uuid: str) -> Mock:
        return requests_mock.post(
            "http://dhos-locations/dhos/v1/location", json={"uuid": location_uuid}
        )

    @pytest.fixture
    def process_patient_message(
        self, epr_encounter_id: str, connector_message_id: str
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
                        "score_system": "news2",
                    },
                },
            ],
        }

    def test_process_no_existing_entities(
        self,
        mock_get_patient_by_identifiers: Mock,
        mock_post_patient: Mock,
        mock_get_location_by_ods_code: Mock,
        mock_post_location: Mock,
        mock_publish: Mock,
        process_patient_message: Dict,
        connector_message_id: str,
        product_uuid: str,
        patient_record_uuid: str,
    ) -> None:
        """
        Tests that when there are no existing patients/locations, new ones are
        created and an "update encounter" message (dhos.305058001) is published.
        """
        # Arrange
        message_body = json.dumps(process_patient_message)

        # Act
        patient_update.process(message_body)

        # Assert
        assert mock_get_patient_by_identifiers.call_count == 2
        assert mock_post_patient.call_count == 1
        assert mock_get_location_by_ods_code.call_count == 4
        assert mock_post_location.call_count == 3
        assert mock_publish.call_count == 1
        publish_call_kwargs = mock_publish.call_args[1]
        assert publish_call_kwargs["routing_key"] == "dhos.305058001"
        actual_published_message_body = publish_call_kwargs["body"]
        assert (
            actual_published_message_body["dhos_connector_message_uuid"]
            == connector_message_id
        )
        assert len(actual_published_message_body["actions"]) == 3
        process_encounter_action = actual_published_message_body["actions"][2]
        assert process_encounter_action["name"] == "process_encounter"
        assert (
            process_encounter_action["data"]["patient_record_uuid"]
            == patient_record_uuid
        )

    def test_process_with_existing_entities(
        self,
        requests_mock: Mocker,
        mock_post_patient: Mock,
        mock_patch_patient: Mock,
        mock_post_location: Mock,
        mock_publish: Mock,
        process_patient_message: Dict,
        patient_uuid: str,
        location_uuid: str,
    ) -> None:
        """
        Tests that when there are preexisting patients/locations, new ones are not
        created, the patient is updated, and an "update encounter" message
        (dhos.305058001) is published.
        """
        # Arrange
        existing_patients = [{"uuid": patient_uuid}]
        mock_get_patient_by_identifiers: Mock = requests_mock.get(
            "http://dhos-services/dhos/v1/patient", json=existing_patients
        )
        existing_locations = {location_uuid: {"uuid": location_uuid}}
        mock_get_location_by_ods_code: Mock = requests_mock.get(
            "http://dhos-locations/dhos/v1/location/search", json=existing_locations
        )
        message_body = json.dumps(process_patient_message)

        # Act
        patient_update.process(message_body)

        # Assert
        assert mock_get_patient_by_identifiers.call_count == 1
        assert mock_post_patient.call_count == 0
        assert mock_patch_patient.call_count == 1
        assert mock_get_location_by_ods_code.call_count == 1
        assert mock_post_location.call_count == 0
        assert mock_publish.call_count == 1

    def test_process_no_encounter_details(
        self,
        mock_get_patient_by_identifiers: Mock,
        mock_post_patient: Mock,
        mock_get_location_by_ods_code: Mock,
        mock_post_location: Mock,
        mock_hl7_message_patch: Mock,
        process_patient_message: Dict,
        product_uuid: str,
        connector_message_id: str,
    ) -> None:
        """
        Tests that when the message contains no encounter or location details,
        the patient is created and the Connector API message is updated.
        """
        # Arrange
        expected_published_message_body = {
            "dhos_connector_message_uuid": connector_message_id,
            "actions": [{"name": "process_message", "data": {"is_processed": True}}],
        }
        # Remove process location and process encounter actions:
        process_patient_message["actions"] = process_patient_message["actions"][:1]
        message_body = json.dumps(process_patient_message)

        # Act
        patient_update.process(message_body)

        # Assert
        assert mock_get_patient_by_identifiers.call_count == 2
        assert mock_post_patient.call_count == 1
        assert mock_get_location_by_ods_code.call_count == 0
        assert mock_post_location.call_count == 0
        assert mock_hl7_message_patch.call_count == 1

    def test_process_patient_merge_no_existing_patient(
        self,
        mock_get_patient_by_identifiers: Mock,
        mock_post_patient: Mock,
        mock_get_location_by_ods_code: Mock,
        mock_post_location: Mock,
        mock_publish: Mock,
        process_patient_message: Dict,
    ) -> None:
        """
        Tests that when there are merge details in the message, the child patient is
        created and merged.
        """
        # Arrange
        process_patient_message["actions"][0]["data"][
            "previous_nhs_number"
        ] = "1234567890"
        process_patient_message["actions"][0]["data"]["previous_mrn"] = "1111111"
        message_body = json.dumps(process_patient_message)

        # Act
        patient_update.process(message_body)

        # Assert
        assert mock_get_patient_by_identifiers.call_count == 4
        assert mock_post_patient.call_count == 2
        assert mock_publish.call_count == 1
        publish_call_kwargs = mock_publish.call_args[1]
        assert publish_call_kwargs["routing_key"] == "dhos.305058001"
        process_encounter_action = publish_call_kwargs["body"]["actions"][2]
        assert process_encounter_action["name"] == "process_encounter"
        assert "merge_patient_record_uuid" in process_encounter_action["data"]

    @pytest.mark.parametrize(
        "primary_uuid,child_uuid,patch_count",
        [("primary-uuid", "primary-uuid", 0), ("primary-uuid", "different-uuid", 1)],
    )
    def test_process_patient_to_merge_preexisting_patient(
        self,
        mocker: MockFixture,
        process_patient_message: Dict,
        primary_uuid: str,
        child_uuid: str,
        patch_count: int,
    ) -> None:
        """
        Tests that when there are merge details in the message, an existing child
        patient is merged.
        """
        # Arrange
        patient_details = {"some": "data"}
        mock_get: Mock = mocker.patch.object(
            patient_update, "_get_existing_patient", return_value={"uuid": child_uuid}
        )
        mock_update: Mock = mocker.patch.object(
            services_api, "update_patient", return_value={"uuid": child_uuid}
        )

        # Act
        patient_update._process_patient_to_merge(
            primary_patient_uuid=primary_uuid,
            patient_data=patient_details,
            previous_nhs_number="1234567890",
            previous_hospital_number="1111111",
        )

        # Assert
        assert mock_get.call_count == 1
        assert mock_update.call_count == patch_count

    def test_multiple_matching_locations_error(
        self,
        requests_mock: Mocker,
        mock_get_patient_by_identifiers: Mock,
        mock_post_patient: Mock,
        mock_patch_patient: Mock,
        mock_post_location: Mock,
        process_patient_message: Dict,
        location_uuid: str,
        caplog: LogCaptureFixture,
    ) -> None:
        # Arrange
        existing_locations = {
            location_uuid: {"uuid": location_uuid},
            "another-location-uuid": {"uuid": "another-location-uuid"},
        }
        mock_get_location_by_ods_code: Mock = requests_mock.get(
            "http://dhos-locations/dhos/v1/location/search", json=existing_locations
        )
        message_body = json.dumps(process_patient_message)

        # Act
        with pytest.raises(RejectMessageError) as e:
            patient_update.process(message_body)

        # Assert
        assert mock_get_location_by_ods_code.call_count == 1
        assert "multiple locations (2)" in caplog.text

    def test_create_location_hierarchy_multiple_matching_locations_success(
        self, requests_mock: Mocker, location_uuid: str
    ) -> None:
        """
        Tests that when the ward exists but the bay/bed don't, the bay and bed are created.
        """
        requests_mock.get(
            "http://dhos-locations/dhos/v1/location/search",
            [
                {"json": {location_uuid: {"uuid": location_uuid}}},
                {"json": {}},
                {"json": {}},
            ],
        )
        mock_location_post = requests_mock.post(
            "http://dhos-locations/dhos/v1/location", json={"uuid": "some-uuid"}
        )
        patient_update._create_location_hierarchy("one:two:three")
        assert mock_location_post.call_count == 2
        assert mock_location_post.request_history[0].json()["ods_code"] == "one:two"
        assert mock_location_post.request_history[0].json()[
            "location_type"
        ] == draymed.codes.code_from_name("bay", category="location")
        assert (
            mock_location_post.request_history[1].json()["ods_code"] == "one:two:three"
        )
        assert mock_location_post.request_history[1].json()[
            "location_type"
        ] == draymed.codes.code_from_name("bed", category="location")

    def test_create_location_hierarchy_multiple_matching_locations_error(
        self, requests_mock: Mocker, location_uuid: str, caplog: LogCaptureFixture
    ) -> None:
        existing_locations = {
            location_uuid: {"uuid": location_uuid},
            "another-location-uuid": {"uuid": "another-location-uuid"},
        }
        requests_mock.get(
            "http://dhos-locations/dhos/v1/location/search", json=existing_locations
        )
        with pytest.raises(RejectMessageError) as e:
            patient_update._create_location_hierarchy("one:two:three")
        assert "multiple locations (2)" in caplog.text

    def test_get_existing_patient_hospital_number(self, mocker: MockFixture) -> None:
        mocker.patch.object(
            services_api,
            "get_patients_by_identifier",
            return_value=[{"uuid": "some-uuid"}],
        )
        result = patient_update._get_existing_patient(
            nhs_number=None, hospital_number="12345"
        )
        assert result is not None
        assert result["uuid"] == "some-uuid"

    def test_get_existing_patient_no_identifiers(
        self, caplog: LogCaptureFixture
    ) -> None:
        with pytest.raises(RejectMessageError) as e:
            patient_update._get_existing_patient(nhs_number=None, hospital_number=None)
        assert (
            "Can not search for patient as MRN or NHS number is required" in caplog.text
        )

    @pytest.mark.parametrize(
        "location,expected",
        [
            (None, "news2"),
            ({"uuid": "something"}, "news2"),
            ({"uuid": "something", "score_system_default": "meows"}, "meows"),
            ({"uuid": "something", "score_system_default": "news2"}, "news2"),
            (
                {
                    "uuid": "something",
                    "parent": {"uuid": "parent", "score_system_default": "meows"},
                },
                "meows",
            ),
            (
                {
                    "uuid": "something",
                    "parent": {
                        "uuid": "parent",
                        "parent": {"uuid": "parent2", "score_system_default": "meows"},
                    },
                },
                "meows",
            ),
            (
                {
                    "uuid": "something",
                    "score_system_default": "meows",
                    "parent": {"uuid": "parent", "score_system_default": "news2"},
                },
                "meows",
            ),
        ],
    )
    def test_get_score_system_default_for_location(
        self, location: Optional[Dict], expected: str
    ) -> None:
        actual = patient_update._get_score_system_default_for_location(location)
        assert actual == expected
