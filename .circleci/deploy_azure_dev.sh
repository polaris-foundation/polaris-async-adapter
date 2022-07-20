#!/usr/bin/env bash

set -eux

source /usr/local/bin/deployment-helpers-v1.sh

# login to GCP
authenticateToAKS

# Iterate through the deployment names (strings delimited by ;) and set image.
deployFromACR
