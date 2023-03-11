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

import mimetypes
from tempfile import NamedTemporaryFile

from fastapi.responses import FileResponse

from mvtool.models import Project
from mvtool.views.excel.projects import (
    ProjectsExcelView,
    convert_project_to_row,
    get_project_excel_headers,
)
from mvtool.views.projects import ProjectsView


def test_get_project_excel_headers():
    headers = get_project_excel_headers()

    header_names = [h.name for h in headers]
    assert header_names == [
        "Project ID",
        "Project Name",
        "Project Description",
        "Project Completion Progress",
        "Project Verification Progress",
    ]


def test_convert_project_to_row(create_project: Project):
    row = convert_project_to_row(create_project)

    assert row == {
        "Project ID": create_project.id,
        "Project Name": create_project.name,
        "Project Description": create_project.description,
        "Project Completion Progress": create_project.completion_progress,
        "Project Verification Progress": create_project.verification_progress,
    }


def test_convert_project_to_row_none():
    row = convert_project_to_row(None)

    assert row == {
        "Project ID": None,
        "Project Name": None,
        "Project Description": None,
        "Project Completion Progress": None,
        "Project Verification Progress": None,
    }


def test_download_projects_excel(
    projects_excel_view, excel_temp_file: NamedTemporaryFile
):
    filename = "test.xlsx"
    response = projects_excel_view.download_projects_excel(
        [], [], temp_file=excel_temp_file, filename=filename
    )

    assert isinstance(response, FileResponse)
    assert response.filename == filename
    assert response.media_type == mimetypes.types_map.get(".xlsx")
