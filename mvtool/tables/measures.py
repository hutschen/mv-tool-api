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

from ..models import AbstractMeasureInput, Measure, MeasureOutput
from ..utils.temp_file import copy_upload_to_temp_file, get_temp_file
from ..views.documents import get_document_filters, get_document_sort
from ..views.measures import MeasuresView
from .common import Column, ColumnGroup
from .documents import DocumentImport, get_document_only_columns
from .handlers import get_export_labels_handler, hide_columns
from .jira_ import JiraIssueImport, get_jira_issue_columns
from .requirements import RequirementImport, get_requirement_columns


class MeasureImport(AbstractMeasureInput):
    id: int | None = None
    requirement: RequirementImport | None
    document: DocumentImport | None
    jira_issue: JiraIssueImport | None


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
            jira_issue_columns,
            Column("Completion Status", "completion_status"),
            Column("Completion Comment", "completion_comment"),
            Column("Verification Method", "verification_method"),
            Column("Verification Status", "verification_status"),
            Column("Verification Comment", "verification_comment"),
        ],
    )


router = APIRouter()

router.get(
    "/excel/measures/column-names",
    summary="Get column names for measures Excel export",
    response_model=list[str],
    **MeasuresView.kwargs,
)(get_export_labels_handler(get_measure_columns))


@router.get("/excel/measures", response_class=FileResponse, **MeasuresView.kwargs)
def download_measures_excel(
    measures_view: MeasuresView = Depends(),
    where_clauses=Depends(get_document_filters),
    sort_clauses=Depends(get_document_sort),
    columns: ColumnGroup = Depends(hide_columns(get_measure_columns)),
    temp_file=Depends(get_temp_file(".xlsx")),
    sheet_name="Measures",
    filename="measures.xlsx",
) -> FileResponse:
    measures = measures_view.list_measures(where_clauses, sort_clauses)
    df = columns.export_to_dataframe(measures)
    df.to_excel(temp_file, sheet_name=sheet_name, index=False, engine="openpyxl")
    return FileResponse(temp_file.name, filename=filename)


@router.post(
    "/excel/measures",
    status_code=201,
    response_model=list[MeasureOutput],
    **MeasuresView.kwargs,
)
def upload_measures_excel(
    measures_view: MeasuresView = Depends(),
    columns: ColumnGroup = Depends(get_measure_columns),
    temp_file=Depends(copy_upload_to_temp_file),
    dry_run: bool = False,
) -> list[Measure]:
    df = pd.read_excel(temp_file, engine="openpyxl")
    measure_imports = columns.import_from_dataframe(df)
    list(measure_imports)
    # TODO: validate measure imports and perform import
    return []
