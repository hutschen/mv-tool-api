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

from typing import Any
from tempfile import NamedTemporaryFile
from fastapi.responses import FileResponse
from fastapi_utils.cbv import cbv
from fastapi import APIRouter, Depends

from .common import ExcelHeader, ExcelView
from ..projects import ProjectsView, get_project_filters, get_project_sort
from ...utils import get_temp_file
from ...models import Project

router = APIRouter()


def get_project_excel_headers() -> list[ExcelHeader]:
    return [
        ExcelHeader("Project ID", optional=True),
        ExcelHeader("Project Name"),
        ExcelHeader("Project Description", optional=True),
        ExcelHeader("Project Completion Progress", ExcelHeader.WRITE_ONLY, True),
        ExcelHeader("Project Verification Progress", ExcelHeader.WRITE_ONLY, True),
    ]


def convert_project_to_row(project: Project | None) -> dict[str, Any]:
    if not project:
        return {
            "Project ID": None,
            "Project Name": None,
            "Project Description": None,
            "Project Completion Progress": None,
            "Project Verification Progress": None,
        }
    return {
        "Project ID": project.id,
        "Project Name": project.name,
        "Project Description": project.description,
        "Project Completion Progress": project.completion_progress,
        "Project Verification Progress": project.verification_progress,
    }


@cbv(router)
class ProjectsExcelView(ExcelView):
    kwargs = dict(tags=["excel"])

    def __init__(
        self,
        projects: ProjectsView = Depends(),
        headers: list[ExcelHeader] = Depends(get_project_excel_headers),
    ):
        ExcelView.__init__(self, headers)
        self._projects = projects

    def _convert_to_row(self, project: Project) -> dict[str, Any]:
        return convert_project_to_row(project)

    @router.get("/excel/projects", response_class=FileResponse, **kwargs)
    def download_projects_excel(
        self,
        where_clauses=Depends(get_project_filters),
        order_by_clauses=Depends(get_project_sort),
        temp_file: NamedTemporaryFile = Depends(get_temp_file(".xlsx")),
        sheet_name: str = "Projects",
        filename: str = "projects.xlsx",
    ) -> FileResponse:
        return self._process_download(
            self._projects.list_projects(where_clauses, order_by_clauses),
            temp_file,
            sheet_name=sheet_name,
            filename=filename,
        )
