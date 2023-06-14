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

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db.database import get_session
from ..handlers.projects import Projects, get_project_filters, get_project_sort
from ..models import Project, ProjectImport, ProjectOutput
from ..utils.temp_file import get_temp_file
from .columns import Column, ColumnGroup
from .dataframe import DataFrame, write_excel
from .handlers import get_export_labels_handler, get_uploaded_dataframe, hide_columns
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


router = APIRouter(tags=["project"])

router.get(
    "/excel/projects/column-names",
    summary="Get column names for projects Excel export",
    response_model=list[str],
)(get_export_labels_handler(get_project_columns))


@router.get("/excel/projects", response_class=FileResponse)
def download_projects_excel(
    projects_view: Projects = Depends(),
    where_clauses=Depends(get_project_filters),
    sort_clauses=Depends(get_project_sort),
    columns: ColumnGroup = Depends(hide_columns(get_project_columns)),
    temp_file=Depends(get_temp_file(".xlsx")),
    sheet_name="Projects",
    filename="projects.xlsx",
) -> FileResponse:
    projects = projects_view.list_projects(where_clauses, sort_clauses)
    write_excel(columns.export_to_dataframe(projects), temp_file, sheet_name)
    return FileResponse(temp_file.name, filename=filename)


@router.post("/excel/projects", status_code=201, response_model=list[ProjectOutput])
def upload_projects_excel(
    projects_view: Projects = Depends(),
    columns: ColumnGroup = Depends(get_project_columns),
    df: DataFrame = Depends(get_uploaded_dataframe),
    skip_blanks: bool = False,  # skip blank cells
    dry_run: bool = False,  # don't save to database
    session: Session = Depends(get_session),
) -> list[Project]:
    # Import the data frame
    project_imports = columns.import_from_dataframe(df, skip_none=skip_blanks)
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
