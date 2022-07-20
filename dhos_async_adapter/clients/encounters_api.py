from typing import Dict, List

from she_logging import logger

from dhos_async_adapter import config
from dhos_async_adapter.clients import do_request
from dhos_async_adapter.helpers.timestamps import generate_iso8601_timestamp


def merge_encounters_with_parent(encounters: List[Dict], parent_uuid: str) -> None:
    payload: Dict = {"child_of_encounter_uuid": parent_uuid}
    for e in encounters:
        updated_encounter: Dict = update_encounter_by_uuid(e["uuid"], payload)
        logger.debug(
            "Merged encounter '%s' with parent '%s'",
            updated_encounter["uuid"],
            parent_uuid,
        )


def get_encounter_by_uuid(encounter_uuid: str, show_deleted: bool = False) -> Dict:
    url = f"{config.DHOS_ENCOUNTERS_API_URL}/dhos/v1/encounter/{encounter_uuid}"
    logger.debug(
        "GETting encounter %s",
        encounter_uuid,
        extra={"url": url},
    )
    response = do_request(url=url, method="get", params={"show_deleted": show_deleted})
    return response.json()


def get_open_local_encounters(patient_uuid: str) -> List[Dict]:
    url = f"{config.DHOS_ENCOUNTERS_API_URL}/dhos/v2/encounter"
    logger.debug(
        "GETting open encounters for patient %s",
        patient_uuid,
        extra={"url": url},
    )
    params = {
        "patient_id": patient_uuid,
        "open_as_of": generate_iso8601_timestamp(),
    }
    response = do_request(
        url=url,
        method="get",
        params=params,
    )

    open_encounters: List[Dict] = response.json()
    logger.debug(
        "Retrieved %d open encounters for patient %s",
        len(open_encounters),
        patient_uuid,
    )
    return [o for o in open_encounters if not o["epr_encounter_id"]]


def get_epr_encounters(patient_uuid: str, epr_encounter_id: str) -> List[Dict]:
    url = f"{config.DHOS_ENCOUNTERS_API_URL}/dhos/v2/encounter"
    logger.debug(
        "GETting EPR encounters for patient %s",
        patient_uuid,
        extra={"url": url},
    )
    response = do_request(
        url=url,
        method="get",
        params={"patient_id": patient_uuid, "epr_encounter_id": epr_encounter_id},
    )
    epr_encounters: List[Dict] = response.json()
    logger.debug(
        "Retrieved %d EPR encounters for patient %s", len(epr_encounters), patient_uuid
    )
    return epr_encounters


def update_encounter_by_uuid(encounter_uuid: str, encounter_data: Dict) -> Dict:
    url = f"{config.DHOS_ENCOUNTERS_API_URL}/dhos/v1/encounter/{encounter_uuid}"
    logger.debug(
        "PATCHing encounter %s",
        encounter_uuid,
        extra={"url": url},
    )
    if "patient_uuid" in encounter_data:
        del encounter_data["patient_uuid"]
    response = do_request(url=url, method="patch", payload=encounter_data)
    return response.json()


def create_encounter(encounter_data: Dict) -> Dict:
    url = f"{config.DHOS_ENCOUNTERS_API_URL}/dhos/v2/encounter"
    logger.debug(
        "POSTing encounter",
        extra={"url": url},
    )
    response = do_request(url=url, method="post", payload=encounter_data)
    return response.json()


def merge_patient_encounters(
    child_record_uuid: str,
    parent_record_uuid: str,
    parent_patient_uuid: str,
    message_uuid: str,
) -> None:
    url = f"{config.DHOS_ENCOUNTERS_API_URL}/dhos/v1/encounter/merge"
    logger.debug(
        "POSTing patient encounter merge",
        extra={"url": url},
    )
    payload = {
        "child_record_uuid": child_record_uuid,
        "parent_record_uuid": parent_record_uuid,
        "parent_patient_uuid": parent_patient_uuid,
        "message_uuid": message_uuid,
    }
    do_request(url=url, method="post", payload=payload)


def get_child_encounters(encounter_uuid: str, show_deleted: bool = False) -> List[str]:
    url = (
        f"{config.DHOS_ENCOUNTERS_API_URL}/dhos/v1/encounter/{encounter_uuid}/children"
    )
    logger.debug(
        "GETting child encounters for encounter %s",
        encounter_uuid,
        extra={"url": url},
    )
    response = do_request(url=url, method="get", params={"show_deleted": show_deleted})
    return response.json()
