# coding: utf-8
#
# Copyright (C) 2022 Helmar Hutschenreuter
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

import io
from unittest.mock import Mock
from fastapi import HTTPException
from fastapi.responses import FileResponse
from openpyxl import load_workbook
import pytest

from mvtool.models import (
    Document,
    Measure,
    Project,
    Requirement,
    RequirementInput,
)
from mvtool.views.excel import (
    DocumentsExcelView,
    MeasuresExcelView,
    RequirementsExcelView,
)


def test_read_worksheet():
    sut = RequirementsExcelView(None)
    workbook = load_workbook("tests/data/excel/requirements_valid.xlsx")
    worksheet = workbook.active

    results = list(sut._read_worksheet(worksheet))

    assert len(results) >= 1
    result = results[0]
    assert isinstance(result, RequirementInput)


def test_read_worksheet_invalid_headers():
    sut = RequirementsExcelView(None)
    workbook = load_workbook("tests/data/excel/requirements_invalid_headers.xlsx")
    worksheet = workbook.active

    with pytest.raises(HTTPException) as error_info:
        list(sut._read_worksheet(worksheet))

    assert error_info.value.status_code == 400
    assert error_info.value.detail.startswith("Missing headers")


def test_read_worksheet_invalid_data():
    sut = RequirementsExcelView(None)
    workbook = load_workbook("tests/data/excel/requirements_invalid_data.xlsx")
    worksheet = workbook.active

    with pytest.raises(HTTPException) as error_info:
        list(sut._read_worksheet(worksheet))

    assert error_info.value.status_code == 400
    assert error_info.value.detail.startswith("Invalid data")


def test_query_measure_data(
    measures_excel_view: MeasuresExcelView,
    create_project: Project,
    create_measure: Measure,
):
    results = list(
        measures_excel_view._query_measure_data(
            Requirement.project_id == create_project.id
        )
    )

    assert len(results) == 1
    result = results[0]
    assert isinstance(result, tuple)
    measure, requirement, document, jira_issue = result
    assert isinstance(measure, Measure)
    assert isinstance(requirement, Requirement)
    assert document == create_measure.document
    assert jira_issue == None


def test_download_measures_excel_for_project(
    measures_excel_view: MeasuresExcelView,
    excel_temp_file,
    create_project: Project,
    create_measure: Measure,
):
    result = measures_excel_view.download_measures_excel_for_project(
        create_project.id, temp_file=excel_temp_file
    )
    assert isinstance(result, FileResponse)
    assert (
        result.media_type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_download_measures_excel_for_requirement(
    measures_excel_view: MeasuresExcelView,
    excel_temp_file,
    create_requirement: Requirement,
    create_measure: Measure,
):
    result = measures_excel_view.download_measures_excel_for_requirement(
        create_requirement.id, temp_file=excel_temp_file
    )
    assert isinstance(result, FileResponse)
    assert (
        result.media_type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_upload_measures_excel(
    measures_excel_view: MeasuresExcelView,
    excel_temp_file,
    create_requirement: Requirement,
):
    upload_file = Mock()
    upload_file.file = io.FileIO("tests/data/excel/measures_valid.xlsx", "r")

    measures_excel_view.upload_measures_excel(
        create_requirement.id, upload_file, excel_temp_file
    )

    assert create_requirement.measures is not None
    assert len(create_requirement.measures) > 0


def test_download_requirements_excel(
    requirements_excel_view: RequirementsExcelView,
    excel_temp_file,
    create_project: Project,
    create_requirement: Requirement,
):
    result = requirements_excel_view.download_requirements_excel(
        create_project.id, temp_file=excel_temp_file
    )
    assert isinstance(result, FileResponse)
    assert (
        result.media_type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_upload_requirements_excel(
    requirements_excel_view: RequirementsExcelView,
    excel_temp_file,
    create_project: Project,
):
    upload_file = Mock()
    upload_file.file = io.FileIO("tests/data/excel/requirements_valid.xlsx", "r")

    requirements_excel_view.upload_requirements_excel(
        create_project.id, upload_file, excel_temp_file
    )

    assert create_project.requirements is not None
    assert len(create_project.requirements) > 0


@pytest.mark.skip()
def test_download_documents_excel(
    export_documents_view: DocumentsExcelView,
    excel_temp_file,
    create_project: Project,
    create_document: Document,
):
    result = export_documents_view.download_documents_excel(
        create_project.id, temp_file=excel_temp_file
    )
    assert isinstance(result, FileResponse)
    assert (
        result.media_type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
