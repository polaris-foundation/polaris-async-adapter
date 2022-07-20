.PHONY: lint pyenv test-local

gitroot = ${shell git rev-parse --show-toplevel}
repo = ${notdir ${gitroot}}
PROJECT_NAME ?= ${repo}
python_version = 3.9.5
VIRTUAL_ENV=${shell pyenv root}/versions/${python_version}/envs/${PROJECT_NAME}-integration-tests

TEST_CONTAINER = ${PROJECT_NAME:-api=}-integration-tests

lint:
	black .
	isort --profile black .
	mypy clients/ helpers/ steps/ --ignore-missing-imports --disallow-untyped-defs

test-local: lint
	docker-compose down -v -t 1
	docker-compose pull
	docker-compose build
	docker-compose up --no-start --force-recreate
	docker-compose run ${TEST_CONTAINER}
	docker-compose down

pyenv:
	pyenv virtualenv ${python_version} ${VIRTUAL_ENV}
	pyenv local ${VIRTUAL_ENV}
	pip install -r requirements
