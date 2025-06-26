PYTHON_VERSION = "3.11.6"
VENV_NAME := $(shell basename $(PWD))

_configure_redis_password:
	./docker.sh run --rm redis redis-cli -a $(REDIS_PASSWORD) CONFIG SET requirepass $(REDIS_PASSWORD)

build:
	./docker.sh build

down:
	./docker.sh down

restart: stop run

run:
	./docker.sh up -d

setup:
	./scripts/setup.sh

stop:
	./docker.sh stop

generate-migration:
	./docker.sh run --rm api alembic revision --autogenerate -m "$(m)"

create-empty-migration:
	./docker.sh run --rm api alembic revision -m "$(m)"

migrate:
	./docker.sh run --rm api alembic upgrade head

test:
	MODE=test ./docker.sh run --rm -it test pytest tests

_install_python_version:
	echo "\n>Install Python version in pyenv if it doesn't exist yet..."
	echo Saving "$(VENV_NAME)" in .python-version
	echo $(VENV_NAME) > .python-version
	echo "-- Checking python pyenv $ installation..."
	if pyenv versions | grep -q $(PYTHON_VERSION); then \
		echo "- python $(PYTHON_VERSION) installation was found in pyenv"; \
	else \
		echo "- python $(PYTHON_VERSION) installation was not found in pyenv, installing it..."; \
		pyenv install $(PYTHON_VERSION); \
	fi

_install_virtualenv:
	# Resets virtual env
	echo "\n>Installing virtual env..."
	echo "- Uninstalling previous venv..."
	pyenv uninstall -f $(VENV_NAME)
	echo "- Installing venv..."
	pyenv virtualenv $(PYTHON_VERSION) $(VENV_NAME)
	pip install --upgrade wheel pip

_install_packages:
	echo "Installing local packages"
	pip3 install -r backend/core/requirements.txt
	pip3 install -r backend/core/requirements-test.txt
	pip3 install -r backend/indexer/requirements.txt
	pip3 install -r backend/api/requirements.txt

_install_pre_commit_hooks:
	pre-commit install

_create_local_env_files:
	# Check if ./config/env exists and creates it by copying ./config/env_template content otherwise
	if [ -d "./config/env" ]; then \
  		echo "Env directory already exists"; \
  	else \
  	  	echo "Creating local env variables"; \
  		cp -R ./config/env_template ./config/env; \
		echo "Env variables target created. Please, provide actual values before running application"; \
  	fi

setup-venv: \
	_install_python_version \
	_install_virtualenv \
	_install_packages \
	_install_pre_commit_hooks \
	_create_local_env_files

generate-local-certs:
	# Wait for confirmation from user to generate new certificates
	@echo "This will generate new local certificates, are you sure you want to continue? [y/N] "; \
	read REPLY; \
	if [ "$$REPLY" != "y" ] && [ "$$REPLY" != "Y" ]; then \
		exit 1; \
	fi
	# Remove existing certificates or ignore if they don't exist
	rm -r certs || true

	mkdir certs
	mkcert -cert-file certs/local-cert.pem -key-file certs/local-key.pem "localhost"


include config/env/.core.env
