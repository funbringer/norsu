.PHONY: all
all: style fmt

.PHONY: fmt
fmt: pipenv-install
	pipenv run yapf -r -i .

.PHONY: style
style: pipenv-install
	pipenv run flake8

.PHONY: pipenv-install
pipenv-install:
	pipenv install --ignore-pipfile --dev

.PHONY: install
install:
	pip install --user .
