from typing import Dict

import requests


def get_audit_events(jwt: str) -> requests.Response:
    return requests.get(
        url="http://dhos-audit-api:5000/dhos/v2/event",
        timeout=15,
        headers={"Authorization": f"Bearer {jwt}"},
    )


def get_sms_messages(jwt: str) -> requests.Response:
    return requests.get(
        url="http://dhos-sms-api:5000/dhos/v1/sms",
        timeout=15,
        headers={"Authorization": f"Bearer {jwt}"},
    )


def create_reading(
    patient_uuid: str, reading_details: Dict, jwt: str
) -> requests.Response:
    return requests.post(
        url=f"http://gdm-bg-readings-api:5000/gdm/v1/patient/{patient_uuid}/reading",
        timeout=15,
        headers={"Authorization": f"Bearer {jwt}"},
        json=reading_details,
    )


def get_bg_readings_patient(patient_uuid: str, jwt: str) -> requests.Response:
    return requests.get(
        url=f"http://gdm-bg-readings-api:5000/gdm/v1/patient/{patient_uuid}",
        timeout=15,
        headers={"Authorization": f"Bearer {jwt}"},
    )


def post_observation_set(obs_set: Dict, jwt: str) -> requests.Response:
    return requests.post(
        url=f"http://dhos-observations-api:5000/dhos/v2/observation_set",
        timeout=15,
        headers={"Authorization": f"Bearer {jwt}"},
        json=obs_set,
    )


def get_encounters_by_epr_id(
    patient_uuid: str, epr_encounter_id: str, jwt: str
) -> requests.Response:
    return requests.get(
        url=f"http://dhos-encounters-api:5000/dhos/v2/encounter",
        timeout=15,
        headers={"Authorization": f"Bearer {jwt}"},
        params={"patient_id": patient_uuid, "epr_encounter_id": epr_encounter_id},
    )


def create_encounter(encounter: Dict, jwt: str) -> requests.Response:
    return requests.post(
        url=f"http://dhos-encounters-api:5000/dhos/v2/encounter",
        timeout=15,
        headers={"Authorization": f"Bearer {jwt}"},
        json=encounter,
    )


def get_encounter_by_uuid(
    encounter_uuid: str, jwt: str, show_deleted: bool = False
) -> requests.Response:
    return requests.get(
        url=f"http://dhos-encounters-api:5000/dhos/v1/encounter/{encounter_uuid}",
        timeout=15,
        headers={"Authorization": f"Bearer {jwt}"},
        params={"show_deleted": show_deleted},
    )


def get_surveys(jwt: str) -> requests.Response:
    return requests.get(
        url=f"http://dhos-questions-api:5000/dhos/v1/survey",
        timeout=15,
        headers={"Authorization": f"Bearer {jwt}"},
    )


def get_activation_auth_clinician_jwt(
    send_entry_identifier: str, jwt: str
) -> requests.Response:
    return requests.get(
        url=f"http://dhos-activation-auth-api:5000/dhos/v1/clinician/jwt",
        timeout=15,
        headers={"Authorization": f"Bearer {jwt}"},
        params={"send_entry_identifier": send_entry_identifier},
    )


def get_message_by_sender_and_receiver_id(
    sender_id: str, receiver_id: str, jwt: str
) -> requests.Response:
    return requests.get(
        url=f"http://dhos-messages-api:5000/dhos/v1/sender/{sender_id}/receiver/{receiver_id}/message",
        timeout=15,
        headers={"Authorization": f"Bearer {jwt}"},
    )


def get_message_by_sender_or_receiver_id(unique_id: str, jwt: str) -> requests.Response:
    return requests.get(
        url=f"http://dhos-messages-api:5000/dhos/v1/sender_or_receiver/{unique_id}/message",
        timeout=15,
        headers={"Authorization": f"Bearer {jwt}"},
    )
