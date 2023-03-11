# coding: utf-8
#
# Copyright (C) 2023 Helmar Hutschenreuter
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from unittest.mock import Mock

import pytest
from openpyxl import Workbook

from mvtool.utils import get_temp_file
from mvtool.views.excel.catalog_modules import get_catalog_module_excel_headers
from mvtool.views.excel.catalog_requirements import (
    get_catalog_requirement_excel_headers,
)
from mvtool.views.excel.catalogs import CatalogsExcelView, get_catalog_excel_headers
from mvtool.views.excel.common import ExcelHeader
from mvtool.views.excel.documents import (
    DocumentsExcelView,
    get_document_excel_headers,
    get_document_excel_headers_only,
)
from mvtool.views.excel.measures import MeasuresExcelView, get_measure_excel_headers
from mvtool.views.excel.projects import get_project_excel_headers
from mvtool.views.excel.requirements import (
    RequirementsExcelView,
    get_requirement_excel_headers,
)


@pytest.fixture
def worksheet_rows():
    return [
        {"int": 0, "str": "hello", "bool": True, "float": 1.0},
        {"int": 1, "str": "world", "bool": False, "float": 2.0},
        {"int": 2, "str": None, "bool": False, "float": 2.5},
    ]


@pytest.fixture
def worksheet_headers():
    return [
        ExcelHeader("int"),
        ExcelHeader("str"),
        ExcelHeader("bool"),
        ExcelHeader("float"),
    ]


@pytest.fixture
def empty_worksheet():
    return Workbook().active


@pytest.fixture
def filled_worksheet(empty_worksheet, worksheet_rows):
    headers = None
    for row in worksheet_rows:
        if not headers:
            headers = [k for k, _ in row.items()]
            empty_worksheet.append(headers)
        empty_worksheet.append(row[h] for h in headers)
    return empty_worksheet


@pytest.fixture
def excel_temp_file():
    for file in get_temp_file(".xlsx")():
        yield file


@pytest.fixture
def catalog_headers():
    return get_catalog_excel_headers()


@pytest.fixture
def catalog_module_headers(catalog_headers):
    return get_catalog_module_excel_headers(catalog_headers)


@pytest.fixture
def catalog_requirement_headers(catalog_module_headers):
    return get_catalog_requirement_excel_headers(catalog_module_headers)


@pytest.fixture
def project_headers():
    return get_project_excel_headers()


@pytest.fixture
def requirement_headers(project_headers, catalog_requirement_headers):
    return get_requirement_excel_headers(project_headers, catalog_requirement_headers)


@pytest.fixture
def document_headers(project_headers):
    document_headers_only = get_document_excel_headers_only()
    return get_document_excel_headers(project_headers, document_headers_only)


@pytest.fixture
def measure_headers(requirement_headers, document_headers):
    return get_measure_excel_headers(requirement_headers, document_headers)


@pytest.fixture
def catalogs_excel_view(catalogs_view, catalog_headers):
    return CatalogsExcelView(catalogs_view, catalog_headers)


@pytest.fixture
def requirements_excel_view(
    crud, projects_view, requirements_view, requirement_headers
):
    return RequirementsExcelView(
        crud.session, projects_view, requirements_view, requirement_headers
    )


@pytest.fixture
def documents_excel_view(crud, projects_view, documents_view, document_headers):
    return DocumentsExcelView(
        crud.session, projects_view, documents_view, document_headers
    )


@pytest.fixture
def measures_excel_view(crud, jira_issues_view, measures_view, measure_headers):
    return MeasuresExcelView(
        crud.session, jira_issues_view, measures_view, measure_headers
    )
