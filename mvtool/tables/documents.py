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


from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
import pandas as pd

from mvtool.utils.temp_file import copy_upload_to_temp_file, get_temp_file
from mvtool.views.documents import (
    DocumentsView,
    get_document_filters,
    get_document_sort,
)

from ..models import Document, DocumentInput, DocumentOutput
from .common import Column, ColumnsDef
from .projects import get_project_columns_def


class DocumentImport(DocumentInput):
    id: int | None = None


def get_document_only_columns_def() -> ColumnsDef[DocumentImport, Document]:
    return ColumnsDef(
        DocumentImport,
        "Document",
        [
            Column("ID", "id"),
            Column("Reference", "reference"),
            Column("Title", "title", required=True),
            Column("Description", "description"),
        ],
    )


def get_document_columns_def(
    project_columns_def: ColumnsDef = Depends(get_project_columns_def),
    document_only_columns_def: ColumnsDef = Depends(get_document_only_columns_def),
) -> ColumnsDef[DocumentImport, Document]:
    project_columns_def.attr_name = "project"
    document_only_columns_def.children.insert(0, project_columns_def)
    return document_only_columns_def


router = APIRouter()


@router.get("/excel/documents", response_class=FileResponse, **DocumentsView.kwargs)
def download_documents_excel(
    documents_view: DocumentsView = Depends(),
    where_clauses=Depends(get_document_filters),
    sort_clauses=Depends(get_document_sort),
    columns_def: ColumnsDef = Depends(get_document_columns_def),
    temp_file=Depends(get_temp_file(".xlsx")),
    sheet_name="Documents",
    filename="documents.xlsx",
) -> FileResponse:
    documents = documents_view.list_documents(where_clauses, sort_clauses)
    df = columns_def.export_to_dataframe(documents)
    df.to_excel(temp_file, sheet_name=sheet_name, index=False, engine="openpyxl")
    return FileResponse(temp_file.name, filename=filename)


@router.post(
    "/excel/documents",
    status_code=201,
    response_model=list[DocumentOutput],
    **DocumentsView.kwargs
)
def upload_documents_excel(
    documents_view: DocumentsView = Depends(),
    columns_def: ColumnsDef = Depends(get_document_columns_def),
    temp_file=Depends(copy_upload_to_temp_file),
    dry_run: bool = False,
) -> list[Document]:
    df = pd.read_excel(temp_file, engine="openpyxl")
    document_imports = columns_def.import_from_dataframe(df)
    list(document_imports)
    # TODO: validate document imports and perform import
    return []
