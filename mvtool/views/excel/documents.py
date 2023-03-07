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
from typing import Iterator
from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse
from fastapi_utils.cbv import cbv
from pydantic import ValidationError
from sqlmodel import Session, select

from mvtool import errors
from mvtool.database import get_session
from mvtool.models import Document, DocumentOutput, DocumentInput
from .common import ExcelHeader, ExcelView, IdModel, get_excel_temp_file
from ..documents import DocumentsView, get_document_filters, get_document_sort
from ..projects import ProjectsView


router = APIRouter()


@cbv(router)
class DocumentsExcelView(ExcelView):
    kwargs = dict(tags=["excel"])

    def __init__(
        self,
        session: Session = Depends(get_session),
        projects: ProjectsView = Depends(ProjectsView),
        documents: DocumentsView = Depends(DocumentsView),
    ):
        ExcelView.__init__(
            self,
            [
                ExcelHeader("ID", optional=True),
                ExcelHeader("Reference", optional=True),
                ExcelHeader("Title"),
                ExcelHeader("Description", optional=True),
            ],
        )
        self._session = session
        self._projects = projects
        self._documents = documents

    def _convert_to_row(self, data: Document) -> dict[str, str]:
        return {
            "ID": data.id,
            "Reference": data.reference,
            "Title": data.title,
            "Description": data.description,
        }

    @router.get(
        "/excel/documents",
        response_class=FileResponse,
        **kwargs,
    )
    def download_documents_excel(
        self,
        where_clauses=Depends(get_document_filters),
        order_by_clauses=Depends(get_document_sort),
        temp_file: NamedTemporaryFile = Depends(get_excel_temp_file),
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
        temp_file: NamedTemporaryFile = Depends(get_excel_temp_file),
    ) -> Iterator[Document]:
        return self._bulk_create_update_documents(
            project_id, self._process_upload(upload_file, temp_file)
        )
