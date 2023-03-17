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


from fastapi import APIRouter, Depends, UploadFile
from fastapi_utils.cbv import cbv
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlmodel import Session, select
from tempfile import NamedTemporaryFile
from typing import Iterator

from ...utils import errors
from ...database import get_session
from ...models import Document, DocumentOutput, DocumentInput
from ...utils.temp_file import get_temp_file
from ..documents import DocumentsView, get_document_filters, get_document_sort
from ..projects import ProjectsView
from .common import ExcelHeader, ExcelView, IdModel
from .projects import convert_project_to_row, get_project_excel_headers

router = APIRouter()


def get_document_excel_headers_only() -> list[ExcelHeader]:
    return [
        ExcelHeader("Document ID", optional=True),
        ExcelHeader("Document Reference", optional=True),
        ExcelHeader("Document Title"),
        ExcelHeader("Document Description", optional=True),
    ]


def get_document_excel_headers(
    project_headers=Depends(get_project_excel_headers),
    document_headers=Depends(get_document_excel_headers_only),
) -> list[ExcelHeader]:
    return [
        *project_headers,
        *document_headers,
    ]


def convert_document_to_row(
    document: Document | None, document_only=False
) -> dict[str, str]:
    project_row = (
        convert_project_to_row(document.project if document else None)
        if not document_only
        else {}
    )
    if not document:
        return {
            **project_row,
            "Document ID": None,
            "Document Reference": None,
            "Document Title": None,
            "Document Description": None,
        }
    return {
        **project_row,
        "Document ID": document.id,
        "Document Reference": document.reference,
        "Document Title": document.title,
        "Document Description": document.description,
    }


@cbv(router)
class DocumentsExcelView(ExcelView):
    kwargs = dict(tags=["excel"])

    def __init__(
        self,
        session: Session = Depends(get_session),
        projects: ProjectsView = Depends(ProjectsView),
        documents: DocumentsView = Depends(DocumentsView),
        headers: list[ExcelHeader] = Depends(get_document_excel_headers),
    ):
        ExcelView.__init__(self, headers)
        self._session = session
        self._projects = projects
        self._documents = documents

    def _convert_to_row(self, data: Document) -> dict[str, str]:
        return convert_document_to_row(data)

    @router.get(
        "/excel/documents",
        response_class=FileResponse,
        **kwargs,
    )
    def download_documents_excel(
        self,
        where_clauses=Depends(get_document_filters),
        order_by_clauses=Depends(get_document_sort),
        temp_file: NamedTemporaryFile = Depends(get_temp_file(".xlsx")),
        sheet_name: str = "Export",
        filename: str = "export.xlsx",
    ) -> FileResponse:
        return self._process_download(
            self._documents.list_documents(where_clauses, order_by_clauses),
            temp_file,
            sheet_name=sheet_name,
            filename=filename,
        )

    def _convert_from_row(
        self, row: dict[str, str], worksheet, row_no: int
    ) -> tuple[int | None, DocumentInput]:
        # Convert the row to a DocumentInput
        try:
            document_id = IdModel(id=row["ID"]).id
            document_input = DocumentInput(
                reference=row["Reference"] or None,
                title=row["Title"],
                description=row["Description"] or None,
            )
        except ValidationError as error:
            detail = 'Invalid data on worksheet "%s" at row %d: %s' % (
                worksheet.title,
                row_no + 1,
                error,
            )
            raise errors.ValueHttpError(detail)
        else:
            return document_id, document_input

    def _bulk_create_update_documents(
        self, project_id: int, data: Iterator[tuple[int | None, DocumentInput]]
    ) -> list[Document]:
        # Get project from database and retrieve data
        project = self._projects.get_project(project_id)
        data = list(data)

        # Read documents to be updated from database
        query = select(Document).where(
            Document.id.in_({id for id, _ in data if id is not None}),
            Document.project_id == project_id,
        )
        read_documents = dict((r.id, r) for r in self._session.exec(query).all())

        # Create or update documents
        written_documents = []
        for document_id, document_input in data:
            if document_id is None:
                # Create document
                document = Document.from_orm(document_input)
                document.project = project
            else:
                # Update document
                document = read_documents.get(document_id)
                if document is None:
                    raise errors.NotFoundError(
                        "Document with ID %d not part of project with ID %d"
                        % (document_id, project_id)
                    )
                for key, value in document_input.dict().items():
                    setattr(document, key, value)

            self._documents._set_jira_project(document)
            self._session.add(document)
            written_documents.append(document)

        self._session.flush()
        return written_documents

    @router.post(
        "/projects/{project_id}/documents/excel",
        status_code=201,
        response_model=list[DocumentOutput],
        **kwargs,
    )
    def upload_documents_excel(
        self,
        project_id: int,
        upload_file: UploadFile,
        temp_file: NamedTemporaryFile = Depends(get_temp_file(".xlsx")),
    ) -> Iterator[Document]:
        return self._bulk_create_update_documents(
            project_id, self._process_upload(upload_file, temp_file)
        )
