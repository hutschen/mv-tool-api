serve:
	python ./run.py

test:
	pytest

test-coverage:
	pytest --cov-report html:tests/cov_html --cov-branch --cov=mvtool . 
	open tests/cov_html/index.html -a Google\ Chrome

dependencies-lock:
	pipenv lock --keep-outdated

dependencies-prod-install:
	pipenv install --ignore-pipfile

dependencies-dev-install:
	pipenv install --dev