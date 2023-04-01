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


from tempfile import NamedTemporaryFile

import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlmodel import Session

from ..database import get_session
from ..models import Requirement, RequirementOutput
from ..models.requirements import RequirementImport
from ..utils.temp_file import copy_upload_to_temp_file, get_temp_file
from ..handlers.catalog_modules import CatalogModulesView
from ..handlers.catalog_requirements import (
    get_catalog_requirement_filters,
    get_catalog_requirement_sort,
)
from ..handlers.projects import ProjectsView
from ..handlers.requirements import RequirementsView
from .catalog_requirements import get_catalog_requirement_columns
from .common import Column, ColumnGroup
from .handlers import get_export_labels_handler, hide_columns
from .projects import get_project_columns


def get_requirement_columns(
    catalog_requirement_columns: ColumnGroup = Depends(get_catalog_requirement_columns),
    project_columns: ColumnGroup = Depends(get_project_columns),
) -> ColumnGroup[RequirementImport, Requirement]:
    catalog_requirement_columns.attr_name = "catalog_requirement"
    project_columns.attr_name = "project"

    return ColumnGroup(
        RequirementImport,
        "Requirement",
        [
            catalog_requirement_columns,
            project_columns,
            Column("ID", "id"),
            Column("Reference", "reference"),
            Column("Summary", "summary", required=True),
            Column("Description", "description"),
            Column("Compliance Status", "compliance_status"),
            Column("Compliance Comment", "compliance_comment"),
            Column("Target Object", "target_object"),
            Column("Milestone", "milestone"),
        ],
    )


router = APIRouter()

router.get(
    "/excel/requirements/column-names",
    summary="Get column names for requirements Excel export",
    response_model=list[str],
    **RequirementsView.kwargs,
)(get_export_labels_handler(get_requirement_columns))


@router.get(
    "/excel/requirements",
    response_class=FileResponse,
    **RequirementsView.kwargs,
)
def download_requirements_excel(
    requirements_view: RequirementsView = Depends(),
    where_clauses=Depends(get_catalog_requirement_filters),
    sort_clauses=Depends(get_catalog_requirement_sort),
    columns: ColumnGroup = Depends(hide_columns(get_requirement_columns)),
    temp_file: NamedTemporaryFile = Depends(get_temp_file(".xlsx")),
    sheet_name="Requirements",
    filename="requirements.xlsx",
) -> FileResponse:
    requirements = requirements_view.list_requirements(where_clauses, sort_clauses)
    df = columns.export_to_dataframe(requirements)
    df.to_excel(temp_file.name, sheet_name=sheet_name, index=False)
    return FileResponse(temp_file.name, filename=filename)


@router.post(
    "/excel/requirements",
    status_code=201,
    response_model=list[RequirementOutput],
    **RequirementsView.kwargs,
)
def upload_requirements_excel(
    fallback_project_id: int | None = None,
    fallback_catalog_module_id: int | None = None,
    project_view: ProjectsView = Depends(),
    catalog_modules_view: CatalogModulesView = Depends(),
    requirements_view: RequirementsView = Depends(),
    columns: ColumnGroup = Depends(get_requirement_columns),
    temp_file=Depends(copy_upload_to_temp_file),
    skip_blanks: bool = False,  # skip blank cells
    dry_run: bool = False,  # don't save to database
    session: Session = Depends(get_session),
) -> list[Requirement]:
    fallback_project = (
        project_view.get_project(fallback_project_id)
        if fallback_project_id is not None
        else None
    )
    fallback_catalog_module = (
        catalog_modules_view.get_catalog_module(fallback_catalog_module_id)
        if fallback_catalog_module_id is not None
        else None
    )

    # Create a data frame from the uploaded Excel file
    df = pd.read_excel(temp_file, engine="openpyxl")
    df.drop_duplicates(keep="last", inplace=True)

    # Import the data frame
    requirement_imports = columns.import_from_dataframe(df, skip_nan=skip_blanks)
    requirements = list(
        requirements_view.bulk_create_update_requirements(
            requirement_imports,
            fallback_project,
            fallback_catalog_module,
            patch=True,
            skip_flush=dry_run,
        )
    )

    # Rollback if dry run
    if dry_run:
        session.rollback()
        return []
    return requirements
