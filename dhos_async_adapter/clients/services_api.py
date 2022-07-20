from typing import Dict, List, Optional

import requests
from she_logging import logger

from dhos_async_adapter import config
from dhos_async_adapter.clients import do_request
from dhos_async_adapter.helpers.exceptions import RejectMessageError


def get_patient(patient_uuid: str, product_name: Optional[str]) -> Optional[Dict]:
    url = f"{config.DHOS_SERVICES_API_URL}/dhos/v1/patient/{patient_uuid}"
    logger.debug(
        "GETting patient with UUID %s",
        patient_uuid,
        extra={"url": url},
    )
    response: requests.Response = do_request(
        url=url,
        method="get",
        params={"product_name": product_name} if product_name else None,
        allow_http_error=True,
    )
    if response.status_code == 404:
        return None
    if response.status_code not in range(200, 300):
        logger.exception("Unexpected response from API (HTTP %d)", response.status_code)
        raise RejectMessageError()
    return response.json()


def get_patient_by_record_id(record_uuid: str, compact: bool = False) -> Dict:
    url = f"{config.DHOS_SERVICES_API_URL}/dhos/v1/patient/record/{record_uuid}"
    logger.debug(
        "GETting patient with record UUID %s",
        record_uuid,
        extra={"url": url},
    )
    response: requests.Response = do_request(
        url=url, method="get", params={"compact": compact}
    )
    return response.json()


def get_patients_by_identifier(
    identifier: str, identifier_value: Optional[str], product_name: str
) -> List[Dict]:
    params = {
        "identifier_type": identifier,
        "identifier_value": identifier_value,
        "product_name": product_name,
    }
    url = f"{config.DHOS_SERVICES_API_URL}/dhos/v1/patient"
    logger.debug(
        "GETting patients with identifier %s %s",
        identifier,
        identifier_value,
        extra={"url": url},
    )
    response: requests.Response = do_request(url=url, method="get", params=params)
    patients: List[Dict] = response.json()
    logger.debug(
        "Retrieved %d patients matching identifier %s %s",
        len(patients),
        identifier,
        identifier_value,
    )
    return patients


def update_patient(patient_uuid: str, patient_details: Dict) -> Dict:
    url = f"{config.DHOS_SERVICES_API_URL}/dhos/v1/patient/{patient_uuid}"
    logger.debug(
        "PATCHing patient with UUID %s",
        patient_uuid,
        extra={"url": url},
    )
    response: requests.Response = do_request(
        url=url, method="patch", payload=patient_details
    )
    return response.json()


def create_patient(patient_details: Dict) -> Dict:
    url = f"{config.DHOS_SERVICES_API_URL}/dhos/v1/patient"
    params = {"type": "SEND"}
    logger.debug(
        "POSTing patient to Services API",
        extra={"url": url},
    )
    response: requests.Response = do_request(
        url=url, method="post", params=params, payload=patient_details
    )
    return response.json()
