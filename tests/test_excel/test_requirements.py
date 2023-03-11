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
from unittest.mock import Mock

import pytest
from fastapi.responses import FileResponse

from mvtool.models import Project, Requirement, RequirementInput
from mvtool.views.excel.requirements import (
    RequirementsExcelView,
    convert_requirement_to_row,
    get_requirement_excel_headers,
)


def test_get_requirements_excel_headers():
    headers = get_requirement_excel_headers([], [])

    header_names = [h.name for h in headers]
    assert header_names == [
        "Requirement ID",
        "Requirement Reference",
        "Requirement Summary",
        "Requirement Description",
        "Requirement Compliance Status",
        "Requirement Compliance Comment",
        "Requirement Completion Progress",
        "Requirement Verification Progress",
        "Milestone",
        "Target Object",
    ]


def test_convert_requirement_to_row(create_requirement: Requirement):
    row = convert_requirement_to_row(create_requirement)

    # check if row contains all expected key/value pairs
    expected = {
        "Requirement ID": create_requirement.id,
        "Requirement Reference": create_requirement.reference,
        "Requirement Summary": create_requirement.summary,
        "Requirement Description": create_requirement.description,
        "Requirement Compliance Status": create_requirement.compliance_status,
        "Requirement Compliance Comment": create_requirement.compliance_comment,
        "Requirement Completion Progress": create_requirement.completion_progress,
        "Requirement Verification Progress": create_requirement.verification_progress,
        "Milestone": create_requirement.milestone,
        "Target Object": create_requirement.target_object,
    }
    assert all(item in row.items() for item in expected.items())


def test_download_requirements_excel(
    requirements_excel_view: RequirementsExcelView,
    excel_temp_file,
    create_requirement: Requirement,
):
    filename = "test.xlsx"
    response = requirements_excel_view.download_requirements_excel(
        [], [], temp_file=excel_temp_file, filename=filename
    )

    assert isinstance(response, FileResponse)
    assert response.filename == filename
    assert response.media_type == mimetypes.types_map.get(".xlsx")


def test_bulk_create_update_requirements(
    requirements_excel_view: RequirementsExcelView,
    create_project: Project,
    create_requirement: Requirement,
):
    data = [
        (create_requirement.id, RequirementInput(summary="update")),
        (None, RequirementInput(summary="create")),
    ]

    results = list(
        requirements_excel_view._bulk_create_patch_requirements(create_project.id, data)
    )

    assert len(results) == 2
    r1, r2 = results
    assert isinstance(r1, Requirement)
    assert r1.summary == "update"
    assert r1.project.jira_project.id == create_project.jira_project_id

    assert isinstance(r2, Requirement)
    assert r2.summary == "create"
    assert r2.project.jira_project.id == create_project.jira_project_id


@pytest.mark.skip()  # FIXME: fix test after refactoring
def test_upload_requirements_excel(
    requirements_excel_view: RequirementsExcelView,
    excel_temp_file,
    create_project: Project,
):
    upload_file = Mock()
    upload_file.file = io.FileIO("tests/data/excel/requirements_valid.xlsx", "r")

    list(
        requirements_excel_view.upload_requirements_excel(
            create_project.id, upload_file, excel_temp_file
        )
    )

    assert create_project.requirements is not None
    assert len(create_project.requirements) > 0
