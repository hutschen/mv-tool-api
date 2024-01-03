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

from typing import Callable

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db.database import get_session
from ..db.schema import Requirement
from ..handlers.catalog_modules import CatalogModules
from ..handlers.projects import Projects
from ..handlers.requirements import (
    Requirements,
    get_requirement_filters,
    get_requirement_sort,
)
from ..models import RequirementOutput
from ..models.requirements import RequirementImport
from .catalog_requirements import get_catalog_requirement_columns
from .columns import Column, ColumnGroup
from .dataframe import DataFrame
from .handlers import (
    get_dataframe_from_uploaded_csv,
    get_dataframe_from_uploaded_excel,
    get_download_csv_handler,
    get_download_excel_handler,
    get_export_labels_handler,
    hide_columns,
)
from .projects import get_project_only_columns
from .status import get_status_columns


def get_requirement_only_columns() -> ColumnGroup[RequirementImport, Requirement]:
    return ColumnGroup(
        RequirementImport,
        "Requirement",
        [
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


def get_requirement_without_status_columns(
    catalog_requirement_columns: ColumnGroup = Depends(get_catalog_requirement_columns),
    project_columns: ColumnGroup = Depends(get_project_only_columns),
    requirement_columns: ColumnGroup = Depends(get_requirement_only_columns),
) -> ColumnGroup[RequirementImport, Requirement]:
    catalog_requirement_columns.attr_name = "catalog_requirement"
    project_columns.attr_name = "project"
    requirement_columns.columns.insert(0, catalog_requirement_columns)
    requirement_columns.columns.insert(0, project_columns)
    return requirement_columns


def get_requirement_columns(
    requirement_columns: ColumnGroup = Depends(get_requirement_without_status_columns),
    status_columns: tuple[Column] = Depends(get_status_columns),
) -> ColumnGroup[RequirementImport, Requirement]:
    requirement_columns.columns.extend(status_columns)
    return requirement_columns


router = APIRouter(tags=["requirement"])

router.get(
    "/excel/requirements/column-names",
    summary="Get column names for requirements Excel export",
    response_model=list[str],
)(get_export_labels_handler(get_requirement_columns))


def _get_requirements_dataframe(
    requirements: Requirements = Depends(),
    where_clauses=Depends(get_requirement_filters),
    sort_clauses=Depends(get_requirement_sort),
    columns: ColumnGroup = Depends(hide_columns(get_requirement_columns)),
) -> DataFrame:
    requirement_list = requirements.list_requirements(where_clauses, sort_clauses)
    return columns.export_to_dataframe(requirement_list)


router.get(
    "/excel/requirements",
    summary="Download requirements as Excel file",
    response_class=FileResponse,
)(
    get_download_excel_handler(
        _get_requirements_dataframe,
        sheet_name="Requirements",
        filename="requirements.xlsx",
    )
)

router.get(
    "/csv/requirements",
    summary="Download requirements as CSV file",
    response_class=FileResponse,
)(get_download_csv_handler(_get_requirements_dataframe, filename="requirements.csv"))


def _get_upload_requirements_dataframe_handler(
    get_uploaded_dataframe: Callable,
) -> Callable:
    def upload_requirements_dataframe(
        fallback_project_id: int | None = None,
        fallback_catalog_module_id: int | None = None,
        project_view: Projects = Depends(),
        catalog_modules_view: CatalogModules = Depends(),
        requirements_view: Requirements = Depends(),
        columns: ColumnGroup = Depends(get_requirement_columns),
        df: DataFrame = Depends(get_uploaded_dataframe),
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

        # Import the data frame
        requirement_imports = columns.import_from_dataframe(df, skip_none=skip_blanks)
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

    return upload_requirements_dataframe


router.post(
    "/excel/requirements",
    summary="Upload requirements from Excel file",
    status_code=201,
    response_model=list[RequirementOutput],
)(_get_upload_requirements_dataframe_handler(get_dataframe_from_uploaded_excel))

router.post(
    "/csv/requirements",
    summary="Upload requirements from CSV file",
    status_code=201,
    response_model=list[RequirementOutput],
)(_get_upload_requirements_dataframe_handler(get_dataframe_from_uploaded_csv))
