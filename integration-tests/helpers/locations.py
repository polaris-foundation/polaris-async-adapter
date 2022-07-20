import re
import unicodedata
from datetime import datetime, timezone
from functools import partial
from typing import Dict, Optional, Tuple

import draymed
from behave.runner import Context
from clients.locations_api_client import post_location
from requests import Response

HOSPITAL_SNOMED: str = draymed.codes.code_from_name("hospital", "location")
WARD_SNOMED: str = draymed.codes.code_from_name("ward", "location")
BAY_SNOMED: str = draymed.codes.code_from_name("bay", "location")
BED_SNOMED: str = draymed.codes.code_from_name("bed", "location")


def slugify(value: str) -> str:
    """
    Converts a string to ascii, lowercase, punctuation stripped, whitespace replaced by a single dash.
    """
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    value = re.sub(r"[^\w\s_-]", "", value.lower())
    return re.sub(r"[\s_-]+", "-", value).strip("-_")


def location(
    name: str,
    ods_code: str = None,
    location_type: str = WARD_SNOMED,
    product_name: str = "SEND",
    opened_date: datetime = None,
    score_system_default: Optional[str] = None,
    parent: str = None,
    parent_ods_code: str = None,
    uuid: str = None,
) -> Dict:
    if opened_date is None:
        opened_date = datetime.now(tz=timezone.utc)

    if ods_code is None:
        ods_code = slugify(name)

    assert parent is None or parent_ods_code is None

    location: Dict = {
        "dh_products": [
            {
                "product_name": product_name,
                "opened_date": opened_date.isoformat(timespec="milliseconds"),
            }
        ],
        "location_type": location_type,
        "ods_code": ods_code,
        "display_name": name,
        "parent_ods_code": parent_ods_code,
        "parent": parent,
        "uuid": uuid,
    }
    if score_system_default is not None:
        location["score_system_default"] = score_system_default
    return {k: v for k, v in location.items() if v is not None}


hospital_factory = partial(location, location_type=HOSPITAL_SNOMED)
ward_factory = partial(location, location_type=WARD_SNOMED)
bay_factory = partial(location, location_type=BAY_SNOMED)
bed_factory = partial(location, location_type=BED_SNOMED)


def _create_location(context: Context, location_details: Dict) -> str:
    response: Response = post_location(location_details, jwt=context.system_jwt)
    context.create_location_response = response
    assert response.status_code == 200
    uuid: str = response.json()["uuid"]
    return uuid


def create_location(
    context: Context,
    name: str = None,
    ods_code: str = None,
    score_system_default: Optional[str] = None,
) -> Tuple[str, str]:
    """Returns UUID and ods_code for the new location"""
    ward = ward_factory(
        name, ods_code=ods_code, score_system_default=score_system_default
    )
    uuid = _create_location(
        context,
        ward,
    )
    return uuid, ward["ods_code"]


def create_hl7_test_ward(context: Context, score_system_default: Optional[str]) -> None:
    """HL7 tests reference bay and bed in this ward. Create hospital and ward so we can
    set score defaults but let async adapter create the child locations directly"""
    hospital = _create_location(
        context, hospital_factory("Test Hospital", ods_code="H1")
    )
    ward = _create_location(
        context,
        ward_factory(
            "NOC-Ward B",
            ods_code="NOC-Ward B",
            score_system_default=score_system_default,
            parent=hospital,
        ),
    )
    context.location_uuid = ward
