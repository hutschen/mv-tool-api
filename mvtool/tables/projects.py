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

from typing import Callable
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from mvtool.tables.rw_csv import CSVDialect, write_csv

from ..db.database import get_session
from ..db.schema import Project
from ..handlers.projects import Projects, get_project_filters, get_project_sort
from ..models import ProjectImport, ProjectOutput
from ..utils.temp_file import get_temp_file
from .columns import Column, ColumnGroup
from .dataframe import DataFrame
from .handlers import (
    get_dataframe_from_uploaded_csv,
    get_dataframe_from_uploaded_excel,
    get_export_labels_handler,
    hide_columns,
)
from .jira_ import get_jira_project_columns
from .rw_excel import write_excel


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


def _get_projects_dataframe(
    projects: Projects = Depends(),
    where_clauses=Depends(get_project_filters),
    sort_clauses=Depends(get_project_sort),
    columns: ColumnGroup = Depends(hide_columns(get_project_columns)),
) -> DataFrame:
    project_list = projects.list_projects(where_clauses, sort_clauses)
    return columns.export_to_dataframe(project_list)


@router.get("/excel/projects", response_class=FileResponse)
def download_projects_excel(
    df: DataFrame = Depends(_get_projects_dataframe),
    temp_file=Depends(get_temp_file(".xlsx")),
    sheet_name="Projects",
    filename="projects.xlsx",
) -> FileResponse:
    write_excel(df, temp_file, sheet_name)
    return FileResponse(temp_file.name, filename=filename)


@router.get("/csv/projects", response_class=FileResponse)
def download_projects_csv(
    df: DataFrame = Depends(_get_projects_dataframe),
    temp_file=Depends(get_temp_file(".csv")),
    filename="projects.csv",
    encoding="utf-8-sig",
    dialect=Depends(CSVDialect),
) -> FileResponse:
    write_csv(df, temp_file, encoding, dialect)
    temp_file.file.seek(0)  # TODO: move this into write_csv
    response = FileResponse(temp_file.name, filename=filename)
    response.headers["Content-Type"] = "application/octet-stream"  # Enforce download
    return response


def _get_upload_projects_dataframe_handler(
    get_uploaded_dataframe: Callable,
) -> Callable:
    def upload_projects_dataframe(
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

    return upload_projects_dataframe


router.post(
    "/excel/projects",
    summary="Upload projects from Excel file",
    status_code=201,
    response_model=list[ProjectOutput],
)(_get_upload_projects_dataframe_handler(get_dataframe_from_uploaded_excel))

router.post(
    "/csv/projects",
    summary="Upload projects from CSV file",
    status_code=201,
    response_model=list[ProjectOutput],
)(_get_upload_projects_dataframe_handler(get_dataframe_from_uploaded_csv))
