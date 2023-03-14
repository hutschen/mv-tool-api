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
from .common import ColumnDef, ColumnsDef
from .documents import DocumentImport, get_document_only_columns_def
from .jira_ import JiraIssueImport, get_jira_issue_columns_def
from .requirements import RequirementImport, get_requirement_columns_def


class MeasureImport(AbstractMeasureInput):
    id: int | None = None
    requirement: RequirementImport | None
    document: DocumentImport | None
    jira_issue: JiraIssueImport | None


def get_measure_columns_def(
    requirement_columns_def: ColumnsDef = Depends(get_requirement_columns_def),
    document_only_columns_def: ColumnsDef = Depends(get_document_only_columns_def),
    jira_issue_columns_def: ColumnsDef = Depends(get_jira_issue_columns_def),
) -> ColumnsDef[MeasureImport, Measure]:
    requirement_columns_def.attr_name = "requirement"
    document_only_columns_def.attr_name = "document"
    jira_issue_columns_def.attr_name = "jira_issue"

    return ColumnsDef(
        MeasureImport,
        "Measure",
        [
            requirement_columns_def,
            ColumnDef("ID", "id"),
            ColumnDef("Reference", "reference"),
            ColumnDef("Summary", "summary", required=True),
            ColumnDef("Description", "description"),
            document_only_columns_def,
            jira_issue_columns_def,
            ColumnDef("Completion Status", "completion_status"),
            ColumnDef("Completion Comment", "completion_comment"),
            ColumnDef("Verification Method", "verification_method"),
            ColumnDef("Verification Status", "verification_status"),
            ColumnDef("Verification Comment", "verification_comment"),
        ],
    )


router = APIRouter()


@router.get("/excel/measures", response_class=FileResponse, **MeasuresView.kwargs)
def download_measures_excel(
    measures_view: MeasuresView = Depends(),
    where_clauses=Depends(get_document_filters),
    sort_clauses=Depends(get_document_sort),
    columns_def: ColumnsDef = Depends(get_measure_columns_def),
    temp_file=Depends(get_temp_file(".xlsx")),
    sheet_name="Measures",
    filename="measures.xlsx",
) -> FileResponse:
    measures = measures_view.list_measures(where_clauses, sort_clauses)
    df = columns_def.export_to_dataframe(measures)
    df.to_excel(temp_file, sheet_name=sheet_name, index=False, engine="openpyxl")
    return FileResponse(temp_file.name, filename=filename)


@router.post(
    "/excel/measures",
    status_code=201,
    response_model=list[MeasureOutput],
    **MeasuresView.kwargs
)
def upload_measures_excel(
    measures_view: MeasuresView = Depends(),
    columns_def: ColumnsDef = Depends(get_measure_columns_def),
    temp_file=Depends(copy_upload_to_temp_file),
    dry_run: bool = False,
) -> list[Measure]:
    df = pd.read_excel(temp_file, engine="openpyxl")
    measure_imports = columns_def.import_from_dataframe(df)
    list(measure_imports)
    # TODO: validate measure imports and perform import
    return []
