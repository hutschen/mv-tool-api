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


import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..models import Project, ProjectOutput
from ..utils.temp_file import copy_upload_to_temp_file, get_temp_file
from ..views.projects import ProjectsView, get_project_filters, get_project_sort
from .common import Column, ColumnGroup
from .handlers import hide_columns
from .jira_ import JiraProjectImport, get_jira_project_columns


class ProjectImport(BaseModel):
    id: int | None = None
    name: str
    description: str | None
    jira_project: JiraProjectImport | None = None


def get_project_columns(
    jira_project_columns: ColumnGroup = Depends(get_jira_project_columns),
) -> ColumnGroup[ProjectImport, Project]:
    jira_project_columns.attr_name = "jira_project"

    return ColumnGroup(
        ProjectImport,
        "Project",
        [
            Column("ID", "id"),
            Column("Name", "name", required=True),
            Column("Description", "description"),
            jira_project_columns,
            Column(
                "Completion Progress",
                "completion_progress",
                Column.EXPORT_ONLY,
            ),
            Column(
                "Verification Progress",
                "verification_progress",
                Column.EXPORT_ONLY,
            ),
        ],
    )


router = APIRouter()


@router.get("/excel/projects", response_class=FileResponse, **ProjectsView.kwargs)
def download_projects_excel(
    projects_view: ProjectsView = Depends(),
    where_clauses=Depends(get_project_filters),
    sort_clauses=Depends(get_project_sort),
    columns: ColumnGroup = Depends(hide_columns(get_project_columns)),
    temp_file=Depends(get_temp_file(".xlsx")),
    sheet_name="Projects",
    filename="projects.xlsx",
) -> FileResponse:
    projects = projects_view.list_projects(where_clauses, sort_clauses)
    df = columns.export_to_dataframe(projects)
    df.to_excel(temp_file, sheet_name=sheet_name, index=False, engine="openpyxl")
    return FileResponse(temp_file.name, filename=filename)


@router.post(
    "/excel/projects",
    status_code=201,
    response_model=list[ProjectOutput],
    **ProjectsView.kwargs
)
def upload_projects_excel(
    projects_view: ProjectsView = Depends(),
    columns: ColumnGroup = Depends(get_project_columns),
    temp_file=Depends(copy_upload_to_temp_file),
    dry_run: bool = False,  # don't save to database
) -> list[Project]:
    df = pd.read_excel(temp_file, engine="openpyxl")
    project_imports = columns.import_from_dataframe(df)
    list(project_imports)
    # TODO: validate project imports and perform import
    return []
