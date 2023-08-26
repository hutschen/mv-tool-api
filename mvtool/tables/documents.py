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
from ..db.schema import Document
from ..handlers.documents import Documents, get_document_filters, get_document_sort
from ..handlers.projects import Projects
from ..models.documents import DocumentImport, DocumentOutput
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


def _get_documents_dataframe(
    documents: Documents = Depends(),
    where_clauses=Depends(get_document_filters),
    sort_clauses=Depends(get_document_sort),
    columns: ColumnGroup = Depends(hide_columns(get_document_columns)),
) -> DataFrame:
    document_list = documents.list_documents(where_clauses, sort_clauses)
    return columns.export_to_dataframe(document_list)


router.get(
    "/excel/documents",
    summary="Get documents as Excel file",
    response_class=FileResponse,
)(
    get_download_excel_handler(
        _get_documents_dataframe,
        sheet_name="Documents",
        filename="documents.xlsx",
    )
)

router.get(
    "/csv/documents",
    summary="Get documents as CSV file",
    response_class=FileResponse,
)(get_download_csv_handler(_get_documents_dataframe, filename="documents.csv"))


def _get_upload_documents_dataframe_handler(
    get_uploaded_dataframe: Callable,
) -> Callable:
    def upload_documents_dataframe(
        fallback_project_id: int | None = None,
        projects_view: Projects = Depends(),
        documents_view: Documents = Depends(),
        columns: ColumnGroup = Depends(get_document_columns),
        df: DataFrame = Depends(get_uploaded_dataframe),
        skip_blanks: bool = False,  # skip blank cells
        dry_run: bool = False,  # don't save to database
        session: Session = Depends(get_session),
    ) -> list[Document]:
        fallback_project = (
            projects_view.get_project(fallback_project_id)
            if fallback_project_id is not None
            else None
        )

        # Import data frame into database
        document_imports = columns.import_from_dataframe(df, skip_none=skip_blanks)
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

    return upload_documents_dataframe


router.post(
    "/excel/documents",
    summary="Upload documents from Excel file",
    status_code=201,
    response_model=list[DocumentOutput],
)(_get_upload_documents_dataframe_handler(get_dataframe_from_uploaded_excel))

router.post(
    "/csv/documents",
    summary="Upload documents from CSV file",
    status_code=201,
    response_model=list[DocumentOutput],
)(_get_upload_documents_dataframe_handler(get_dataframe_from_uploaded_csv))
