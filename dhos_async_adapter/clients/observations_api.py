from typing import Dict, List

from she_logging import logger

from dhos_async_adapter import config
from dhos_async_adapter.clients import do_request


def get_observation_sets(encounter_uuid: str) -> List[Dict]:
    url = f"{config.DHOS_OBSERVATIONS_API_URL}/dhos/v2/observation_set?encounter_id={encounter_uuid}"
    logger.debug(
        "Getting observation sets for encounter %s",
        encounter_uuid,
        extra={"url": url},
    )
    response = do_request(url=url, method="get")
    return response.json()


def get_observation_sets_for_encounter_ids(encounter_uuids: List[str]) -> List[Dict]:
    url = f"{config.DHOS_OBSERVATIONS_API_URL}/dhos/v2/observation_set"
    logger.debug(
        "Getting observation sets for encounters: %s",
        ", ".join(encounter_uuids),
        extra={"url": url},
    )
    response = do_request(
        url=url, method="get", params={"encounter_id": encounter_uuids}
    )
    return response.json()
