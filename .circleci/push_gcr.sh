#!/usr/bin/env bash

# Create tags
CIRCLE_TAG="cb-${CIRCLE_BUILD_NUM}"
GIT_TAG=`git log --pretty=format:'%h' -n 1`

# Set up GCR auth
echo ${GOOGLE_AUTH} > ${HOME}/gcloud-service-key.json
gcloud --quiet auth activate-service-account ${SERVICE_ACCOUNT_ID} --key-file ${HOME}/gcloud-service-key.json
gcloud --quiet auth configure-docker
gcloud --quiet config set project ${GCP_PROJECT}
gcloud --quiet config set compute/zone ${GCP_COMPUTE_ZONE}

# Tag and push image to GCR
docker tag ${CIRCLE_PROJECT_REPONAME} gcr.io/${GCP_PROJECT}/${CIRCLE_PROJECT_REPONAME}:${CIRCLE_TAG}
docker tag ${CIRCLE_PROJECT_REPONAME} gcr.io/${GCP_PROJECT}/${CIRCLE_PROJECT_REPONAME}:${GIT_TAG}
docker tag ${CIRCLE_PROJECT_REPONAME} gcr.io/${GCP_PROJECT}/${CIRCLE_PROJECT_REPONAME}:${K8S_DEV_TAG}
docker push gcr.io/${GCP_PROJECT}/${CIRCLE_PROJECT_REPONAME}:${K8S_DEV_TAG}
gcloud --quiet container images add-tag gcr.io/${GCP_PROJECT}/${CIRCLE_PROJECT_REPONAME}:${K8S_DEV_TAG} \
    gcr.io/${GCP_PROJECT}/${CIRCLE_PROJECT_REPONAME}:${CIRCLE_TAG} \
    gcr.io/${GCP_PROJECT}/${CIRCLE_PROJECT_REPONAME}:${GIT_TAG}
