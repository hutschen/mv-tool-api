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

import io
import mimetypes
from tempfile import NamedTemporaryFile
from unittest.mock import Mock

import pytest
from fastapi.responses import FileResponse

from mvtool.errors import ValueHttpError
from mvtool.models import JiraIssue, Measure, MeasureInput, Project, Requirement
from mvtool.views.excel.measures import (
    MeasuresExcelView,
    convert_measure_to_row,
    get_measure_excel_headers,
)


def test_get_measures_excel_headers():
    headers = get_measure_excel_headers([], [])

    header_names = [h.name for h in headers]
    assert header_names == [
        "Measure ID",
        "Measure Reference",
        "Measure Summary",
        "Measure Description",
        "Measure Compliance Status",
        "Measure Compliance Comment",
        "Measure Completion Status",
        "Measure Completion Comment",
        "Measure Verification Method",
        "Measure Verification Status",
        "Measure Verification Comment",
        "JIRA Issue Key",
    ]


def test_convert_measure_to_row(create_measure: Measure):
    row = convert_measure_to_row(create_measure)

    # check if row contains all expected key/value pairs
    expected = {
        "Measure ID": create_measure.id,
        "Measure Reference": create_measure.reference,
        "Measure Summary": create_measure.summary,
        "Measure Description": create_measure.description,
        "Measure Compliance Status": create_measure.compliance_status,
        "Measure Compliance Comment": create_measure.compliance_comment,
        "Measure Completion Status": create_measure.completion_status,
        "Measure Completion Comment": create_measure.completion_comment,
        "Measure Verification Method": create_measure.verification_method,
        "Measure Verification Status": create_measure.verification_status,
        "Measure Verification Comment": create_measure.verification_comment,
        "JIRA Issue Key": (
            create_measure.jira_issue.key if create_measure.jira_issue else None
        ),
    }
    assert all(item in row.items() for item in expected.items())


def test_download_measures_excel(
    measures_excel_view: MeasuresExcelView,
    excel_temp_file: NamedTemporaryFile,
    create_measure: Measure,
):
    filename = "test.xlsx"
    response = measures_excel_view.download_measures_excel(
        [], [], temp_file=excel_temp_file, filename=filename
    )

    assert isinstance(response, FileResponse)
    assert response.filename == filename
    assert response.media_type == mimetypes.types_map.get(".xlsx")


def test_bulk_create_patch_measures(
    measures_excel_view: MeasuresExcelView,
    create_project: Project,
    create_requirement: Requirement,
    create_measure: Measure,
    jira_issue: JiraIssue,
):
    create_measure.jira_issue_id = None
    data = [
        (create_measure.id, None, MeasureInput(summary="update")),
        (None, jira_issue.key, MeasureInput(summary="create")),
    ]

    results = list(
        measures_excel_view._bulk_create_patch_measures(create_requirement.id, data)
    )

    assert len(results) == 2
    m1, m2 = results
    assert isinstance(m1, Measure)
    assert m1.summary == "update"
    assert m1.jira_issue == None
    assert m2.requirement.project.jira_project.id == create_project.jira_project.id

    assert isinstance(m2, Measure)
    assert m2.summary == "create"
    assert m2.jira_issue.id == jira_issue.id
    assert m2.requirement.project.jira_project.id == create_project.jira_project.id


def test_convert_row_to_measure(
    empty_worksheet, measures_excel_view: MeasuresExcelView
):
    row = {
        "Reference": "",
        "ID": "1",
        "JIRA Issue Key": "TEST-1",
        "Summary": "test",
        "Description": "test",
        "Compliance Status": "C",
        "Compliance Comment": "test",
        "Completion Status": "open",
        "Completion Comment": "test",
        "Verification Status": "verified",
        "Verification Method": "R",
        "Verification Comment": "test",
    }

    measure_id, jira_issue_key, measure_input = measures_excel_view._convert_from_row(
        row, empty_worksheet, 1
    )
    assert measure_id == 1
    assert jira_issue_key == "TEST-1"
    assert measure_input.summary == "test"
    assert measure_input.description == "test"
    assert measure_input.verification_status == "verified"


def test_convert_row_to_measure_invalid_jira_issue_key(
    empty_worksheet, measures_excel_view: MeasuresExcelView
):
    row = {
        "ID": "1",
        "JIRA Issue Key": " INVALID ",
        "Summary": "test",
        "Description": "test",
        "Verified": False,
        "Verification Method": "R",
        "Verification Comment": "test",
    }

    with pytest.raises(ValueHttpError) as error_info:
        measures_excel_view._convert_from_row(row, empty_worksheet, 1)
        assert error_info.value.detail.startswith("Invalid data on worksheet")


@pytest.mark.skip()  # FIXME: fix test after refactoring
def test_upload_measures_excel(
    measures_excel_view: MeasuresExcelView,
    excel_temp_file,
    create_requirement: Requirement,
):
    upload_file = Mock()
    upload_file.file = io.FileIO("tests/data/excel/measures_valid.xlsx", "r")

    list(
        measures_excel_view.upload_measures_excel(
            create_requirement.id, upload_file, excel_temp_file
        )
    )

    assert create_requirement.measures is not None
    assert len(create_requirement.measures) > 0
