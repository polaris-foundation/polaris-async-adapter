from typing import Callable, Dict, List

from dhos_async_adapter.callbacks import (
    audit_event,
    begin_process_hl7_cda_message,
    bg_reading_abnormal,
    bg_reading_alert,
    check_orphaned_observations,
    create_activation_auth_clinician,
    create_oru_message,
    email,
    encounter_obs_set_notification,
    encounter_update,
    export_gdm_syne_bg_readings,
    generate_send_pdf,
    patient_update,
    update_activation_auth_clinician,
)

# These routes are described in more detail in the README.
ROUTING_TABLE: Dict[str, Dict[str, Callable]] = {
    "dhos-dea-export-adapter-task-queue": {
        export_gdm_syne_bg_readings.ROUTING_KEY: export_gdm_syne_bg_readings.process,
    },
    "dhos-activation-auth-adapter-task-queue": {
        create_activation_auth_clinician.ROUTING_KEY: create_activation_auth_clinician.process,
        update_activation_auth_clinician.ROUTING_KEY: update_activation_auth_clinician.process,
    },
    "dhos-aggregator-adapter-task-queue": {
        generate_send_pdf.ROUTING_KEY: generate_send_pdf.process,
    },
    "dhos-audit-adapter-task-queue": {audit_event.ROUTING_KEY: audit_event.process},
    "dhos-connector-adapter-task-queue": {
        begin_process_hl7_cda_message.ROUTING_KEY: begin_process_hl7_cda_message.process,
    },
    "dhos-encounters-adapter-task-queue": {
        encounter_update.ROUTING_KEY: encounter_update.process,
        encounter_obs_set_notification.ROUTING_KEY: encounter_obs_set_notification.process,
    },
    "dhos-messages-adapter-task-queue": {
        # No longer has messages routed to it.
    },
    "dhos-pdf-adapter-task-queue": {
        # No longer has messages routed to it.
    },
    "dhos-notifications-adapter-task-queue": {email.ROUTING_KEY: email.process},
    "dhos-observations-adapter-task-queue": {
        check_orphaned_observations.ROUTING_KEY: check_orphaned_observations.process
    },
    "dhos-questions-adapter-task-queue": {
        # No longer has messages routed to it.
    },
    "dhos-services-adapter-task-queue": {
        bg_reading_alert.ROUTING_KEY: bg_reading_alert.process,
        create_oru_message.ROUTING_KEY: create_oru_message.process,
        patient_update.ROUTING_KEY: patient_update.process,
    },
    "dhos-sms-adapter-task-queue": {
        # No longer has messages routed to it.
    },
    "gdm-bg-readings-adapter-task-queue": {
        bg_reading_abnormal.ROUTING_KEY: bg_reading_abnormal.process,
    },
}

# Queues to be declared in lazy mode
QUEUE_MODES: Dict[str, str] = {
    "dhos-connector-adapter-task-queue": "lazy",
}

# Deprecated routes that are no longer required and should be removed if they exist.
ROUTES_TO_UNBIND: Dict[str, List[str]] = {
    "dhos-dea-export-adapter-task-queue": [
        "dhos.DM000012",
        "dhos.DM000013",
        "dhos.DM000014",
        "dhos.DM000016",
    ],
    "dhos-connector-adapter-task-queue": [
        "dhos.DM000001",
        "dhos.DM000006",
        "dhos.DM000009",
    ],
    "dhos-encounters-adapter-task-queue": ["dhos.DM000003"],
    "dhos-messages-adapter-task-queue": ["gdm.961331000000105", "gdm.2021801000001109"],
    "dhos-pdf-adapter-task-queue": [
        "dhos.DM000008",
        "dhos.DM000012",
        "gdm.717391000000106",
    ],
    "dhos-questions-adapter-task-queue": ["gdm.25241000000106"],
    "dhos-services-adapter-task-queue": ["dhos.24431000000100"],
    "dhos-sms-adapter-task-queue": ["dhos.936701000000103"],
}

# Flattened version of ROUTING_TABLE in the form:
# {
#     routing_key: callback,
#     ...
# }
CALLBACK_LOOKUP: Dict[str, Callable] = {
    key: callback
    for route_map in ROUTING_TABLE.values()
    for key, callback in route_map.items()
}
