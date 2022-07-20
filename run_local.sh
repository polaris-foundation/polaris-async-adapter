#!/bin/bash

export ENVIRONMENT=DEVELOPMENT
export RABBITMQ_HOST=localhost
export RABBITMQ_USERNAME=guest
export RABBITMQ_PASSWORD=guest
export PROXY_URL=http://localhost
export HS_KEY=secret
export CUSTOMER_CODE=dev
export SMS_DEFAULT_SENDER=GDm-Health
export DEA_AUTH0_CLIENT_ID=something
export DEA_AUTH0_CLIENT_SECRET=something
export DEA_AUTH0_AUDIENCE=something
export DEA_AUTH0_TOKEN_URL=something
export DEA_INGEST_API_URL=http://dea-ingest
export DHOS_ACTIVATION_AUTH_API_URL=http://dhos-activation-auth
export DHOS_AGGREGATOR_API_URL=http://dhos-aggregator
export DHOS_AUDIT_API_URL=http://dhos-audit
export DHOS_CONNECTOR_API_URL=http://dhos-connector
export DHOS_ENCOUNTERS_API_URL=http://dhos-encounters
export DHOS_MESSAGES_API_URL=http://dhos-messages
export DHOS_NOTIFICATIONS_API_URL=http://dhos-notifications
export DHOS_OBSERVATIONS_API_URL=http://dhos-observations
export DHOS_PDF_API_URL=http://dhos-pdf
export DHOS_QUESTIONS_API_URL=http://dhos-questions
export DHOS_SERVICES_API_URL=http://dhos-services
export DHOS_USERS_API_URL=http://dhos-users
export DHOS_SMS_API_URL=http://dhos-sms
export GDM_BG_READINGS_API_URL=http://gdm-bg-readings
export LOG_LEVEL=${LOG_LEVEL:-DEBUG}
export LOG_FORMAT=${LOG_FORMAT:-COLOUR}

python3 -m dhos_async_adapter
