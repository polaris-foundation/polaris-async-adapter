from typing import Dict, List, Optional

import draymed
import requests

WARD_CODE = draymed.codes.code_from_name("ward", category="location")

import json

import requests
from environs import Env

env = Env()
expected_trustomer = env.str("CUSTOMER_CODE").lower()
expected_product = "polaris"
expected_api_key = env.str("POLARIS_API_KEY")
trustomer_config = json.loads(env.str("MOCK_TRUSTOMER_CONFIG"))


def setup_mock_get_trustomer_config() -> None:
    payload = {
        "request": {
            "method": "GET",
            "url": "/dhos-trustomer/dhos/v1/trustomer/dev",
            "headers": {
                "X-Trustomer": {"equalTo": expected_trustomer},
                "X-Product": {"equalTo": expected_product},
                "Authorization": {"equalTo": expected_api_key},
            },
        },
        "response": {"jsonBody": trustomer_config},
    }
    response = requests.post(f"http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def setup_mock_dea_ingest_api() -> None:
    payload = {
        "request": {"method": "POST", "url": "/dea-ingest/dea/ingest/v2/dhos_data"},
        "response": {"status": 200},
    }
    response = requests.post("http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def setup_mock_dea_auth0_tenant() -> None:

    payload = {
        "request": {"method": "POST", "url": "/dea-auth0/token"},
        "response": {"status": 200, "jsonBody": {"access_token": "TOKEN"}},
    }
    response = requests.post("http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def get_mock_dea_ingest_api_calls() -> List[Dict]:
    payload = {"method": "POST", "url": "/dea-ingest/dea/ingest/v2/dhos_data"}
    response = requests.post("http://wiremock:8080/__admin/requests/find", json=payload)
    response.raise_for_status()
    return response.json()["requests"]


def setup_mock_connector_api_patch_hl7() -> None:
    payload = {
        "request": {
            "method": "PATCH",
            "urlPattern": f"/dhos-connector/dhos/v1/message/(.*)",
        },
        "response": {"status": 201},
    }
    response = requests.post("http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def get_mock_connector_api_patch_hl7_calls(message_uuid: str) -> List[Dict]:
    payload = {
        "method": "PATCH",
        "url": f"/dhos-connector/dhos/v1/message/{message_uuid}",
    }
    response = requests.post("http://wiremock:8080/__admin/requests/find", json=payload)
    response.raise_for_status()
    return response.json()["requests"]


def setup_mock_connector_api_post_oru() -> None:
    payload = {
        "request": {"method": "POST", "url": "/dhos-connector/dhos/v1/oru_message"},
        "response": {"status": 204},
    }
    response = requests.post("http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def get_mock_connector_api_post_oru_calls() -> List[Dict]:
    payload = {
        "method": "POST",
        "url": "/dhos-connector/dhos/v1/oru_message",
    }
    response = requests.post("http://wiremock:8080/__admin/requests/find", json=payload)
    response.raise_for_status()
    return response.json()["requests"]


def setup_mock_pdf_api_ward() -> None:
    payload = {
        "request": {"method": "POST", "url": "/dhos-pdf/dhos/v1/ward_report"},
        "response": {"status": 201},
    }
    response = requests.post("http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def get_mock_pdf_api_ward_calls() -> List[Dict]:
    payload = {
        "method": "POST",
        "url": f"/dhos-pdf/dhos/v1/ward_report",
    }
    response = requests.post("http://wiremock:8080/__admin/requests/find", json=payload)
    response.raise_for_status()
    return response.json()["requests"]


def setup_mock_pdf_api_send() -> None:
    payload = {
        "request": {"method": "POST", "url": f"/dhos-pdf/dhos/v1/send_pdf"},
        "response": {"status": 201},
    }
    response = requests.post("http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def get_mock_pdf_api_send_calls() -> List[Dict]:
    payload = {
        "method": "POST",
        "url": f"/dhos-pdf/dhos/v1/send_pdf",
    }
    response = requests.post("http://wiremock:8080/__admin/requests/find", json=payload)
    response.raise_for_status()
    return response.json()["requests"]


def setup_mock_pdf_api_gdm() -> None:
    payload = {
        "request": {"method": "POST", "url": f"/dhos-pdf/dhos/v1/gdm_pdf"},
        "response": {"status": 201},
    }
    response = requests.post("http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def get_mock_pdf_api_gdm_calls() -> List[Dict]:
    payload = {
        "method": "POST",
        "url": f"/dhos-pdf/dhos/v1/gdm_pdf",
    }
    response = requests.post("http://wiremock:8080/__admin/requests/find", json=payload)
    response.raise_for_status()
    return response.json()["requests"]


def setup_mock_aggregator_api_ward_report_data(location_uuid: str) -> None:
    payload = {
        "request": {
            "method": "GET",
            "urlPattern": f"/dhos-aggregator/dhos/v1/send_ward_report_data\\?location_uuid=(.*)&start_date=(.*)&end_date=(.*)",
        },
        "response": {
            "status": 200,
            "jsonBody": {
                "pdf_data": [{"some": "value", "other": "value"}],
                "report_month": "April",
                "report_year": "2019",
                "hospital_name": "some-thing",
                "ward_name": "other-thing",
                "location_uuid": location_uuid,
            },
        },
    }
    response = requests.post("http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def get_mock_aggregator_api_ward_report_data_calls() -> List[Dict]:
    payload = {
        "method": "GET",
        "urlPattern": f"/dhos-aggregator/dhos/v1/send_ward_report_data\\?location_uuid=(.*)&start_date=(.*)&end_date=(.*)",
    }
    response = requests.post("http://wiremock:8080/__admin/requests/find", json=payload)
    response.raise_for_status()
    return response.json()["requests"]


def setup_mock_services_api_get_patient(location_uuid: str) -> None:
    payload = {
        "request": {
            "method": "GET",
            "urlPattern": f"/dhos-services/dhos/v1/patient/(.*)",
        },
        "response": {
            "status": 200,
            "jsonBody": _generate_patient_response(
                patient_uuid="{{request.path.[4]}}",
                product_name="GDM",
                location_uuid=location_uuid,
            ),
            "transformers": ["response-template"],
        },
    }
    response = requests.post("http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def setup_mock_services_api_get_patient_by_record(
    patient_uuid: str, record_uuid: str, product_uuid: str
) -> None:
    payload = {
        "request": {
            "method": "GET",
            "urlPattern": f"/dhos-services/dhos/v1/patient/record/(.*)",
        },
        "response": {
            "status": 200,
            "jsonBody": _generate_patient_response(
                patient_uuid=patient_uuid,
                product_name="SEND",
                record_uuid=record_uuid,
                product_uuid=product_uuid,
            ),
        },
    }
    response = requests.post("http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def setup_mock_services_api_get_patients_by_identifier(
    patient_uuid: str, record_uuid: str, product_uuid: str
) -> None:
    payload = {
        "request": {
            "method": "GET",
            "urlPattern": f"/dhos-services/dhos/v1/patient\\?identifier_type=(.*)",
        },
        "response": {
            "status": 200,
            "jsonBody": [
                _generate_patient_response(
                    patient_uuid=patient_uuid,
                    product_name="SEND",
                    record_uuid=record_uuid,
                    product_uuid=product_uuid,
                )
            ],
        },
    }
    response = requests.post("http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def setup_mock_services_api_patch_patient(record_uuid: str, product_uuid: str) -> None:
    payload = {
        "request": {
            "method": "PATCH",
            "urlPattern": f"/dhos-services/dhos/v1/patient/(.*)",
        },
        "response": {
            "status": 200,
            "jsonBody": _generate_patient_response(
                patient_uuid="{{request.path.[4]}}",
                product_name="SEND",
                record_uuid=record_uuid,
                product_uuid=product_uuid,
            ),
            "transformers": ["response-template"],
        },
    }
    response = requests.post("http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def setup_mock_users_api_get_clinician() -> None:
    payload = {
        "request": {
            "method": "GET",
            "urlPattern": f"/dhos-users/dhos/v1/clinician/(.*)",
        },
        "response": {
            "status": 200,
            "jsonBody": {"uuid": "{{request.path.[4]}}"},
            "transformers": ["response-template"],
        },
    }
    response = requests.post("http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def setup_mock_users_api_retrieve_clinician_list() -> None:
    payload = {
        "request": {
            "method": "POST",
            "urlPattern": "/dhos-users/dhos/v1/clinician_list\\?compact=True",
        },
        "response": {
            "status": 200,
            "jsonBody": {
                "{{jsonPath request.body '$[0]'}}": {
                    "first_name": "Tommy",
                    "last_name": "Shelby",
                }
            },
            "transformers": ["response-template"],
        },
    }
    response = requests.post("http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def get_mock_services_api_get_patient_calls(patient_uuid: str) -> List[Dict]:
    payload = {
        "method": "GET",
        "url": f"/dhos-services/dhos/v1/patient/{patient_uuid}",
    }
    response = requests.post("http://wiremock:8080/__admin/requests/find", json=payload)
    response.raise_for_status()
    return response.json()["requests"]


def _generate_patient_response(
    *,
    patient_uuid: str,
    product_name: str,
    location_uuid: Optional[str] = None,
    record_uuid: Optional[str] = None,
    product_uuid: Optional[str] = None,
) -> Dict:
    return {
        "uuid": patient_uuid,
        "first_name": "Laura",
        "locations": [location_uuid],
        "phone_number": "07777777777",
        "allowed_to_text": True,
        "record": {"uuid": record_uuid},
        "dh_products": [{"product_name": product_name, "uuid": product_uuid}],
    }
