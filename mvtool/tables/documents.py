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
from ..models.documents import Document, DocumentImport, DocumentOutput
from ..utils.temp_file import copy_upload_to_temp_file, get_temp_file
from ..handlers.documents import DocumentsView, get_document_filters, get_document_sort
from ..handlers.projects import Projects
from .common import Column, ColumnGroup
from .handlers import get_export_labels_handler, hide_columns
from .projects import get_project_columns


def get_document_only_columns() -> ColumnGroup[DocumentImport, Document]:
    return ColumnGroup(
        DocumentImport,
        "Document",
        [
            Column("ID", "id"),
            Column("Reference", "reference"),
            Column("Title", "title", required=True),
            Column("Description", "description"),
        ],
    )


def get_document_columns(
    project_columns: ColumnGroup = Depends(get_project_columns),
    document_only_columns: ColumnGroup = Depends(get_document_only_columns),
) -> ColumnGroup[DocumentImport, Document]:
    project_columns.attr_name = "project"
    document_only_columns.columns.insert(0, project_columns)
    return document_only_columns


router = APIRouter(tags=["document"])


router.get(
    "/excel/documents/column-names",
    summary="Get column names for documents Excel export",
    response_model=list[str],
)(get_export_labels_handler(get_document_columns))


@router.get("/excel/documents", response_class=FileResponse)
def download_documents_excel(
    documents_view: DocumentsView = Depends(),
    where_clauses=Depends(get_document_filters),
    sort_clauses=Depends(get_document_sort),
    columns: ColumnGroup = Depends(hide_columns(get_document_columns)),
    temp_file=Depends(get_temp_file(".xlsx")),
    sheet_name="Documents",
    filename="documents.xlsx",
) -> FileResponse:
    documents = documents_view.list_documents(where_clauses, sort_clauses)
    df = columns.export_to_dataframe(documents)
    df.to_excel(temp_file, sheet_name=sheet_name, index=False, engine="openpyxl")
    return FileResponse(temp_file.name, filename=filename)


@router.post("/excel/documents", status_code=201, response_model=list[DocumentOutput])
def upload_documents_excel(
    fallback_project_id: int | None = None,
    projects_view: Projects = Depends(),
    documents_view: DocumentsView = Depends(),
    columns: ColumnGroup = Depends(get_document_columns),
    temp_file=Depends(copy_upload_to_temp_file),
    skip_blanks: bool = False,  # skip blank cells
    dry_run: bool = False,  # don't save to database
    session: Session = Depends(get_session),
) -> list[Document]:
    fallback_project = (
        projects_view.get_project(fallback_project_id)
        if fallback_project_id is not None
        else None
    )

    # Create data frame from uploaded file
    df = pd.read_excel(temp_file, engine="openpyxl")
    df.drop_duplicates(keep="last", inplace=True)

    # Import data frame into database
    document_imports = columns.import_from_dataframe(df, skip_nan=skip_blanks)
    documents = list(
        documents_view.bulk_create_update_documents(
            document_imports, fallback_project, patch=True, skip_flush=dry_run
        )
    )

    # Rollback if dry run
    if dry_run:
        session.rollback()
        return []
    return documents
