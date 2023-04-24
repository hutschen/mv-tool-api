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


import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlmodel import Session

from ..database import get_session
from ..handlers.catalog_modules import CatalogModules
from ..handlers.measures import Measures, get_measure_filters, get_measure_sort
from ..handlers.requirements import Requirements
from ..models import Measure, MeasureImport, MeasureOutput
from ..utils.temp_file import get_temp_file
from .common import Column, ColumnGroup
from .documents import get_document_only_columns
from .handlers import get_export_labels_handler, get_uploaded_dataframe, hide_columns
from .jira_ import get_jira_issue_columns
from .requirements import get_requirement_columns


def get_measure_columns(
    requirement_columns: ColumnGroup = Depends(get_requirement_columns),
    document_only_columns: ColumnGroup = Depends(get_document_only_columns),
    jira_issue_columns: ColumnGroup = Depends(get_jira_issue_columns),
) -> ColumnGroup[MeasureImport, Measure]:
    requirement_columns.attr_name = "requirement"
    document_only_columns.attr_name = "document"
    jira_issue_columns.attr_name = "jira_issue"

    return ColumnGroup(
        MeasureImport,
        "Measure",
        [
            requirement_columns,
            Column("ID", "id"),
            Column("Reference", "reference"),
            Column("Summary", "summary", required=True),
            Column("Description", "description"),
            document_only_columns,
            Column("Compliance Status", "compliance_status"),
            Column("Compliance Comment", "compliance_comment"),
            jira_issue_columns,
            Column("Completion Status", "completion_status"),
            Column("Completion Comment", "completion_comment"),
            Column("Verification Method", "verification_method"),
            Column("Verification Status", "verification_status"),
            Column("Verification Comment", "verification_comment"),
        ],
    )


router = APIRouter(tags=["measure"])


router.get(
    "/excel/measures/column-names",
    summary="Get column names for measures Excel export",
    response_model=list[str],
)(get_export_labels_handler(get_measure_columns))


@router.get("/excel/measures", response_class=FileResponse)
def download_measures_excel(
    measures_view: Measures = Depends(),
    where_clauses=Depends(get_measure_filters),
    sort_clauses=Depends(get_measure_sort),
    columns: ColumnGroup = Depends(hide_columns(get_measure_columns)),
    temp_file=Depends(get_temp_file(".xlsx")),
    sheet_name="Measures",
    filename="measures.xlsx",
) -> FileResponse:
    measures = measures_view.list_measures(where_clauses, sort_clauses)
    df = columns.export_to_dataframe(measures)
    df.to_excel(temp_file, sheet_name=sheet_name, index=False, engine="openpyxl")
    return FileResponse(temp_file.name, filename=filename)


@router.post("/excel/measures", status_code=201, response_model=list[MeasureOutput])
def upload_measures_excel(
    fallback_requirement_id: int | None = None,
    fallback_catalog_module_id: int | None = None,
    measures_view: Measures = Depends(),
    requirements_view: Requirements = Depends(),
    catalog_modules_view: CatalogModules = Depends(),
    columns: ColumnGroup = Depends(get_measure_columns),
    df: pd.DataFrame = Depends(get_uploaded_dataframe),
    skip_blanks: bool = False,  # skip blank cells
    dry_run: bool = False,  # don't save to database
    session: Session = Depends(get_session),
) -> list[Measure]:
    fallback_requirement = (
        requirements_view.get_requirement(fallback_requirement_id)
        if fallback_requirement_id is not None
        else None
    )
    fallback_catalog_module = (
        catalog_modules_view.get_catalog_module(fallback_catalog_module_id)
        if fallback_catalog_module_id is not None
        else None
    )

    # Import the data frame
    measure_imports = columns.import_from_dataframe(df, skip_nan=skip_blanks)
    measures = list(
        measures_view.bulk_create_update_measures(
            measure_imports,
            fallback_requirement,
            fallback_catalog_module,
            patch=True,
            skip_flush=dry_run,
        )
    )

    # Rollback if dry run
    if dry_run:
        session.rollback()
        return []
    return measures
