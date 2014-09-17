# Copyright 2014 package-builder authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
#
CWD="`pwd`"
PROJECT_HOME ?= $(CWD)
PROJECT_CODE =$(PROJECT_HOME)
PROJECT_TEST =$(PROJECT_HOME)/tests
NEW_PYTHONPATH=$(PROJECT_CODE):$(PYTHONPATH)

clean:
	@echo " - Cleaning up *.pyc files"
	@find . -name "*.pyc" -delete

setup:
	@echo " - Installing dependencies..."
	@pip install -r $(PROJECT_HOME)/requirements.txt
	@pip install -r $(PROJECT_HOME)/requirements_test.txt

pep8:
	@echo " - Checking source-code PEP8 compliance"
	@-pep8 $(PROJECT_CODE) --ignore=E501,E126,E127,E128

pep8_tests:
	@echo " - Checking tests code PEP8 compliance"
	@-pep8 $(PROJECT_TEST) --ignore=E501,E126,E127,E128

lint:
	@echo " - Running pylint"
	@pylint $(PROJECT_CODE)/$(PROJECT_NAME) --disable=C0301 --disable=C0103

tests: clean pep8 pep8_tests lint
	@echo " - Running pep8, lint, unit and integration tests..."
	@python $(PROJECT_TEST)/*