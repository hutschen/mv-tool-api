serve:
	python ./run.py

test:
	pytest

test-coverage:
	pytest --cov-report html:tests/cov_html --cov-branch --cov=mvtool . 
	open tests/cov_html/index.html

dependencies-lock:
	pipenv lock --keep-outdated

dependencies-prod-install:
	pipenv install --ignore-pipfile

dependencies-dev-install:
	pipenv install --ignore-pipfile --dev

dependencies-update:
	pipenv update --dev

dependencies-licenses:
	pipenv run pip-licenses --packages \
		fastapi pydantic jira pyyaml fastapi-utils sqlalchemy sqlmodel \
		cachetools openpyxl python-multipart python-docx \
		--with-authors --with-urls --format=md > licenses.md

alembic-revision:
	pipenv run alembic revision --autogenerate -m "$(m)"

alembic-upgrade:
	pipenv run alembic upgrade head