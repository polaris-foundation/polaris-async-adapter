# Polaris Async Adapter

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

The Async Adapter is part of the Polaris platform (formerly DHOS). This service performs asynchronous tasks. Its 
primary role is to act as a consumer for RabbitMQ messages, pulling them off various queues and processing them 
based on their routing key.  


## Maintainers
The Polaris platform was created by Sensyne Health Ltd., and has now been made open-source. As a result, some of the
instructions, setup and configuration will no longer be relevant to third party contributors. For example, some of
the libraries used may not be publicly available, or docker images may not be accessible externally. In addition, 
CICD pipelines may no longer function.

For now, Sensyne Health Ltd. and its employees are the maintainers of this repository.

## Setup
These setup instructions assume you are using out-of-the-box installations of:
- `pre-commit` (https://pre-commit.com/)
- `pyenv` (https://github.com/pyenv/pyenv)
- `poetry` (https://python-poetry.org/)

You can run the following commands locally:
```bash
make install  # Creates a virtual environment using pyenv and installs the dependencies using poetry
make lint  # Runs linting/quality tools including black, isort and mypy
make test  # Runs unit tests
```

You can also run the service locally using the script `run_local.sh`, or in dockerized form by running:
```bash
docker build . -t <tag>
docker run <tag>
```

## Messages
  
The service consumes the following messages:
  
| Routing key          | Queue name                              | Message type                                                            |
| -------------------- | --------------------------------------- | ----------------------------------------------------------------------- |
| dhos.D9000001        | dhos-activation-auth-adapter-task-queue | [Create Activation Auth clinician](#create-activation-auth-clinician)   |
| dhos.D9000002        | dhos-activation-auth-adapter-task-queue | [Update Activation Auth clinician](#update-activation-auth-clinician)   |
| dhos.DM000007        | dhos-aggregator-adapter-task-queue      | [Generate SEND PDF](#generate-send-pdf)                                 |
| dhos.34837004        | dhos-audit-adapter-task-queue           | [Audit event](#audit-event)                                             |
| dhos.423779001       | dhos-connector-adapter-task-queue       | [Begin HL7 CDA processing](#begin-hl7-cda-processing)                   |
| dhos.DM000015        | dhos-dea-export-adapter-task-queue      | [Export GDM SYNE BG readings](#export-gdm-syne-bg-readings)             |
| dhos.305058001       | dhos-encounters-adapter-task-queue      | [Encounter update](#encounter-update)                                   |
| dhos.DM000004        | dhos-encounters-adapter-task-queue      | [Encounters obs set notification](#encounters-obs-set-notification)     |
| dhos.DM000002        | dhos-observations-adapter-task-queue    | [Check orphaned observations](#check-orphaned-observations)             |
| dhos.DM000017        | dhos-services-adapter-task-queue        | [Email message](#email-message)                                         |
| gdm.424167000        | dhos-services-adapter-task-queue        | [BG reading alert](#bg-reading-alert)                                   |
| dhos.DM000005        | dhos-services-adapter-task-queue        | [Create ORU message](#create-oru-message)                               |
| dhos.24891000000101  | dhos-services-adapter-task-queue        | [Patient update](#patient-update)                                       |
| gdm.166922008        | gdm-bg-readings-adapter-task-queue      | [Abnormal BG reading](#abnormal-bg-reading)                             |

### Create Activation Auth clinician

- **Summary**: Creates a clinician in Activation Auth API.
- **Routing Key**: dhos.D9000001
- **Body**: A clinician's details.
- **Notes**: Used for creating SEND Entry login credentials.
- **Endpoint(s)**: _POST /dhos-activation-auth/dhos/v1/clinician_

### Update Activation Auth clinician

- **Summary**: Updates a clinician in Activation Auth API.
- **Routing Key**: dhos.D9000001
- **Body**: A clinician's details.
- **Notes**: Used for updating SEND Entry login credentials.
- **Endpoint(s)**: _PATCH /dhos-activation-auth/dhos/v1/clinician/<clinician_uuid>_

### Generate SEND PDF

- **Summary**: Generate summary report PDF on a SEND encounter (hospital stay).
- **Routing Key**: dhos.DM000007
- **Body**: An object containing an encounter ID.
- **Notes**: Aggregates data and generates SEND PDF.
- **Endpoint(s)**: 
  - _GET /dhos-encounters/dhos/v1/encounter/<encounter_uuid>_
  - _GET /dhos-encounters/dhos/v1/encounter/<encounter_uuid>/children_
  - _GET /dhos-services/dhos/v1/patient/record/<record_uuid>_
  - _GET /dhos-locations/dhos/v1/location/<location_uuid>_
  - _GET /dhos-observations/dhos/v2/observation_set_
  - _POST /dhos-users/dhos/v1/clinician_list_
  - _POST /dhos-pdf/dhos/v1/send_pdf_

### Audit event

- **Summary:** Records an audit event in the Audit API service.
- **Routing Key:** dhos.34837004
- **Body:** Details of the audit event.
- **Notes:** This is our primary mechanism for recording specific audit events.  
- **Endpoint(s):** _POST /dhos-audit/dhos/v2/event_

### Begin HL7 CDA processing
- **Summary:** Begin processing HL7 CDA message using the Connector API.
- **Routing Key:** dhos.423779001
- **Body:** Details of a HL7 CDA message
- **Notes:** Used for async ACK.
- **Endpoint(s):** _POST /dhos-connector/dhos/v1/cda_message_

### Export GDM SYNE BG readings

- **Summary**: Exports GDM SYNE blood glucose readings to DEA Ingest API.
- **Routing Key**: dhos.DM000015
- **Body**: GDM SYNE blood glucose readings reports.
- **Notes**: Reports are sent to the central DEA Ingest API.
- **Endpoint(s)**: _POST /dea/ingest/v2/dhos_data_ (external)

### Encounter update

- **Summary:** Processes an encounter update received via HL7 messages, and updates Encounters API as appropriate.
- **Routing Key:** dhos.305058001
- **Body:** A group of actions in the format published by the Connector API service.
- **Notes:** Encounter updating logic is complex and may include creating, updating or merging various encounters.  
- **Endpoint(s):**
    - _GET /dhos-encounters/dhos/v2/encounter_
    - _POST /dhos-encounters/dhos/v2/encounter_
    - _PATCH /dhos-encounters/dhos/v1/encounter/<encounter_uuid>_
    - _POST /dhos-encounters/dhos/v1/encounter/merge_
    - _PATCH /dhos-connector/dhos/v1/message/<message_uuid>_

### Encounters obs set notification

- **Summary:** Appends encounter information from Encounters API to a published observation set notification.
- **Routing Key:** dhos.DM000004
- **Body:** A group of actions in the format published by the Connector API service.
- **Notes:** Part of the chain that results in an ORU HL7  message. Results in an dhos.DM000005 message being published.
- **Endpoint(s):**
    - _GET /dhos-encounters/dhos/v1/encounter/<encounter_uuid>_
    - _POST /dhos-encounters/dhos/v2/encounter_
    - _PATCH /dhos-encounters/dhos/v1/encounter/<encounter_uuid>_

### Check orphaned observations

- **Summary:** Checks for orphaned observations sets in Observations API and merges them if required.
- **Routing Key:** dhos.DM000002
- **Body:** A group of actions in the format published by the Connector API service.
- **Notes:** Merges encounter in Encounters API if required, then updates message in Connector API.
- **Endpoint(s):**
  - _GET /dhos-observations/dhos/v2/observation_set_
  - _GET /dhos-encounters/dhos/v1/encounter/<encounter_uuid>_
  - _POST /dhos-encounters/dhos/v2/encounter_
  - _PATCH /dhos-encounters/dhos/v1/encounter/<encounter_uuid>_
  - _PATCH /dhos-connector/dhos/v1/message/<message_uuid>_
  
### Email message

- **Summary:** Sends an email message via the Notifications API service.
- **Routing Key:** dhos.DM000017
- **Body:** Details of an email message.
- **Notes:** Includes email address and email type.
- **Endpoint(s):** _POST /dhos-notifications/dhos/v1/email_

### BG reading alert

- **Summary**: Sends BG readings alert messages using the Messages API.
- **Routing Key**: gdm.424167000
- **Body**: An object containing a patient UUID and alert type
- **Notes**: Sends an alert message to each location the patient belongs to. Aborts if patient is not a GDM patient.
- **Endpoint(s)**:
  - _GET /dhos-services/dhos/v1/patient_
  - _POST /dhos-messages/dhos/v1/message_

### Create ORU message

- **Summary**: Creates an ORU message in Connector API.
- **Routing Key**: dhos.DM000005
- **Body**: A group of actions in the format published by the Connector API service.
- **Notes**: Appends patient data to existing encounter/observation data and triggers sending of an ORU message.
- **Endpoint(s)**:
    - _GET /dhos-services/dhos/v1/patient/record/<record_uuid>_
    - _GET /dhos-users/dhos/v1/clinician/<clinician_uuid>_
    - _GET /dhos-locations/dhos/v1/location/<location_uuid>_
    - _POST /dhos-connector/dhos/v1/oru_message_

### Patient update

- **Summary**: Processes a patient update received via HL7 messages, and updates Services API as appropriate.
- **Routing Key**: dhos.24891000000101
- **Body**: A group of actions in the format published by the Connector API service.
- **Notes**: Creates or updates patients and locations as appropriate, then publishes dhos.305058001 or updates message in Connector API.
- **Endpoint(s)**:
    - _GET /dhos-services/dhos/v1/patient_
    - _POST /dhos-services/dhos/v1/patient_
    - _PATCH /dhos-services/dhos/v1/patient/<patient_uuid>_
    - _GET /dhos-locations/dhos/v1/location/search_
    - _PATCH /dhos-connector/dhos/v1/message/<message_uuid>_

### Abnormal bg reading

- **Summary:** Triggers processing of an abnormal blood glucose reading in the BG Readings API service.
- **Routing Key:** gdm.166922008
- **Body:** Details of a blood glucose reading that was flagged as abnormal.
- **Notes:** This mechanism is how GDM "counts" alerts are generated.
- **Endpoint(s):** _POST /gdm-bg-readings/gdm/v1/process_alerts/reading/<reading_uuid>_

## TODO: Self-publishes

The Async Adapter performs the roles that were originally performed by multiple adapter workers. For this reason, there
are several places where Async Adapter is effectively publishing messages to itself (via RabbitMQ).

Where those messages are not published by any other service (e.g. API services), these situations should be removed, given that Async Adapter can simply chain tasks rather than publishing and consuming.

These are listed below:
- "Patient update" (dhos.24891000000101) can produce "Encounter update" (dhos.305058001)
- "Encounter update" (dhos.305058001) can produce "Check orphaned observations" (dhos.DM000002)

## Integration tests
The integration tests run on a git push as part of the CICD pipeline. They spin up Async Adapter as well as some dependencies using docker-compose, and then execute some containerised `behave` tests.

Some of the dependencies are mocked using Wiremock, which stands up dummy versions of some endpoints. This lets us get away with not running every single one of the services Async Adapter talks to.
