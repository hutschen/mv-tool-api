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
from mvtool.views.excel.common import ExcelHeader
from mvtool.views.excel.documents import DocumentsExcelView
from mvtool.views.excel.measures import MeasuresExcelView
from mvtool.views.excel.requirements import RequirementsExcelView


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
def measures_excel_view(crud, jira_issues_view, measures_view):
    return Mock(wraps=MeasuresExcelView(crud.session, jira_issues_view, measures_view))


@pytest.fixture
def requirements_excel_view(crud, projects_view, requirements_view):
    return Mock(
        wraps=RequirementsExcelView(crud.session, projects_view, requirements_view)
    )


@pytest.fixture
def documents_excel_view(crud, projects_view, documents_view):
    return Mock(wraps=DocumentsExcelView(crud.session, projects_view, documents_view))
