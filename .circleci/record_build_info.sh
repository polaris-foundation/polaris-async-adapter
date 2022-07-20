#!/usr/bin/env bash

# Record what circle build number created the image.
echo ${CIRCLE_BUILD_NUM} > build-circleci.txt

# Record what the git commit hash of the code in the image
echo `git log --pretty=format:'%h' -n 1` > build-githash.txt

# Record the version of the software by looking at the latest tag.
REVISION=$(git tag -l --format="%(creatordate:short)|%(refname:short)" | sort -r | head -n 1 | cut -d'|' -f 2)
if ! git describe --exact-match --tags HEAD>/dev/null 2>&1
then
  REVISION+="-dev"
fi
echo ${REVISION} > build-version.txt
