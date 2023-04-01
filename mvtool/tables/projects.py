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
from sqlmodel import Session

from ..database import get_session
from ..models import Project, ProjectImport, ProjectOutput
from ..utils.temp_file import copy_upload_to_temp_file, get_temp_file
from ..handlers.projects import ProjectsView, get_project_filters, get_project_sort
from .common import Column, ColumnGroup
from .handlers import get_export_labels_handler, hide_columns
from .jira_ import get_jira_project_columns


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

router.get(
    "/excel/projects/column-names",
    summary="Get column names for projects Excel export",
    response_model=list[str],
    **ProjectsView.kwargs
)(get_export_labels_handler(get_project_columns))


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
    skip_blanks: bool = False,  # skip blank cells
    dry_run: bool = False,  # don't save to database
    session: Session = Depends(get_session),
) -> list[Project]:
    # Create a data frame from the uploaded Excel file
    df = pd.read_excel(temp_file, engine="openpyxl")
    df.drop_duplicates(keep="last", inplace=True)

    # Import the data frame
    project_imports = columns.import_from_dataframe(df, skip_nan=skip_blanks)
    projects = list(
        projects_view.bulk_create_update_projects(
            project_imports, patch=True, skip_flush=dry_run
        )
    )

    # Rollback if dry run
    if dry_run:
        session.rollback()
        return []
    return projects
