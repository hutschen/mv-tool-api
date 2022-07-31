serve:
	python ./run.py

test:
	pytest

test-coverage:
	pytest --cov-report html:tests/cov_html --cov-branch --cov=mvtool . 
	open tests/cov_html/index.html -a Google\ Chrome