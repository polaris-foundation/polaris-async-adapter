from pathlib import Path

from environs import Env

DEFAULT_SYSTEM_JWT_SCOPE: str = " ".join(
    [
        "read:gdm_message_all",
        "read:gdm_patient_all",
        "read:gdm_clinician_all",
        "read:gdm_location_all",
        "read:location_by_ods",
        "read:patient_all",
        "read:send_clinician_all",
        "read:send_encounter",
        "read:send_location",
        "read:send_observation",
        "read:send_patient",
        "write:audit_event",
        "write:gdm_alert",
        "write:gdm_message_all",
        "write:gdm_patient_all",
        "write:send_patient",
        "write:gdm_pdf",
        "write:gdm_sms",
        "write:gdm_survey",
        "write:gdm_location",
        "write:send_location",
        "write:hl7_message",
        "write:send_clinician",
        "write:send_encounter",
        "write:send_pdf",
        "write:ward_report",
    ]
)

env: Env = Env()

# Trustomer settings
SMS_DEFAULT_SENDER = env.str("SMS_DEFAULT_SENDER")
CUSTOMER_CODE: str = env.str("CUSTOMER_CODE")
ENVIRONMENT: str = env.str("ENVIRONMENT")
PROXY_URL = env.str("PROXY_URL")

# Authentication
HS_KEY: str = env.str("HS_KEY")
SYSTEM_JWT_SCOPE: str = env.str(
    "SYSTEM_JWT_SCOPE",
    default=DEFAULT_SYSTEM_JWT_SCOPE,
)
SYSTEM_JWT_EXPIRY_SEC: int = env.int("SYSTEM_JWT_EXPIRY_SEC", default=300)
DEA_AUTH0_CLIENT_ID: str = env.str("DEA_AUTH0_CLIENT_ID")
DEA_AUTH0_CLIENT_SECRET: str = env.str("DEA_AUTH0_CLIENT_SECRET")
DEA_AUTH0_AUDIENCE: str = env.str("DEA_AUTH0_AUDIENCE")
DEA_AUTH0_TOKEN_URL: str = env.str("DEA_AUTH0_TOKEN_URL")

# URLs for services we need to talk to
DEA_INGEST_API_URL: str = env.str("DEA_INGEST_API_URL")
DHOS_ACTIVATION_AUTH_API_URL: str = env.str("DHOS_ACTIVATION_AUTH_API_URL")
DHOS_AGGREGATOR_API_URL: str = env.str("DHOS_AGGREGATOR_API_URL")
DHOS_AUDIT_API_URL: str = env.str("DHOS_AUDIT_API_URL")
DHOS_CONNECTOR_API_URL: str = env.str("DHOS_CONNECTOR_API_URL")
DHOS_ENCOUNTERS_API_URL: str = env.str("DHOS_ENCOUNTERS_API_URL")
DHOS_LOCATIONS_API_URL = env.str("DHOS_LOCATIONS_API_URL")
DHOS_MESSAGES_API_URL: str = env.str("DHOS_MESSAGES_API_URL")
DHOS_NOTIFICATIONS_API_URL: str = env.str("DHOS_NOTIFICATIONS_API_URL")
DHOS_OBSERVATIONS_API_URL: str = env.str("DHOS_OBSERVATIONS_API_URL")
DHOS_PDF_API_URL: str = env.str("DHOS_PDF_API_URL")
DHOS_SERVICES_API_URL = env.str("DHOS_SERVICES_API_URL")
DHOS_USERS_API_URL = env.str("DHOS_USERS_API_URL")
GDM_BG_READINGS_API_URL = env.str("GDM_BG_READINGS_API_URL")

# Build information
circleci_file: Path = Path(__file__).parent.parent / "build-circleci.txt"
githash_file: Path = Path(__file__).parent.parent / "build-githash.txt"
BUILD_CIRCLE_TAG: str = (
    circleci_file.read_text().strip() if circleci_file.exists() else "unknown"
)
BUILD_GIT_TAG: str = (
    githash_file.read_text().strip() if githash_file.exists() else "unknown"
)
