# coding: utf-8
#
# Copyright (C) 2022 Helmar Hutschenreuter
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


import shutil
from tempfile import NamedTemporaryFile
from typing import Any, Collection, Generic, TypeVar
from fastapi import APIRouter, Depends, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi_utils.cbv import cbv
from pydantic import ValidationError
from pyparsing import Iterator
from sqlmodel import Session, select
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.table import Table
from mvtool import errors

from mvtool.database import get_session
from mvtool.models import (
    Document,
    JiraIssue,
    Measure,
    MeasureInput,
    Requirement,
    RequirementInput,
    DocumentInput,
)
from .jira_ import JiraIssuesView
from .measures import MeasuresView
from .requirements import RequirementsView
from .documents import DocumentsView


def get_excel_temp_file():
    with NamedTemporaryFile(suffix=".xlsx") as temp_file:
        yield temp_file


router = APIRouter()
T = TypeVar("T")


class ExcelHeader:
    READ_WRITE = 0
    READ_ONLY = 1
    WRITE_ONLY = 2

    def __init__(self, name: str, mode: int | None = None, optional: bool = False):
        self.name = name
        self._mode = mode or self.READ_WRITE
        self.optional = optional

    @property
    def is_write(self) -> bool:
        return self._mode in (self.READ_WRITE, self.WRITE_ONLY)

    @property
    def is_read(self) -> bool:
        return self._mode in (self.READ_WRITE, self.READ_ONLY)


class ExcelView(Generic[T]):
    def __init__(self, headers: Collection[ExcelHeader]):
        self._write_headers = [header for header in headers if header.is_write]
        self._read_headers = [header for header in headers if header.is_read]

    def _convert_to_row(self, data: T) -> dict[str, str]:
        raise NotImplementedError("Must be implemented by subclass")

    def _write_preprocessing(
        self, data: Iterator[T]
    ) -> tuple[list[str], dict[str, str]]:
        header_names: set[str] = set()
        rows: list[dict[str, str]] = []

        # Convert data to rows and determine headers
        for row_data in data:
            row = self._convert_to_row(row_data)
            for header in self._write_headers:
                if header.optional and not row[header.name]:
                    continue
                header_names.add(header.name)
            rows.append(row)

        # Arrange headers in the order they are defined
        header_names = [h.name for h in self._write_headers if h.name in header_names]
        return header_names, rows

    def _write_worksheet(
        self,
        worksheet: Worksheet,
        data: Iterator[T],
    ):
        header_names, rows = self._write_preprocessing(data)

        # Fill worksheet with data
        worksheet.append(header_names)
        is_empty = True
        for row in rows:
            values = [row.get(h_name, "") for h_name in header_names]
            worksheet.append(values)
            is_empty = False

        # Add table to worksheet
        if not is_empty:
            table = Table(
                displayName=worksheet.title, ref=worksheet.calculate_dimension()
            )
            worksheet.add_table(table)

    def _convert_from_row(self, row: dict[str, str], worksheet, row_no) -> T:
        raise NotImplementedError("Must be implemented by subclass")

    def _read_worksheet(
        self,
        worksheet: Worksheet,
    ) -> Iterator[T]:
        required_header_names = {h.name for h in self._read_headers if not h.optional}
        worksheet_header_names = None
        is_header_row = True

        for row_index, row in enumerate(worksheet.iter_rows(values_only=True)):
            if is_header_row:
                # Check if all headers are present
                if not required_header_names.issubset(row):
                    detail = 'Missing headers on worksheet "%s": %s' % (
                        worksheet.title,
                        ", ".join(required_header_names - set(row)),
                    )
                    raise errors.ValueHttpError(detail)
                worksheet_header_names = tuple(row)
                is_header_row = False
            else:
                # Convert row to dict and yield
                yield self._convert_from_row(
                    {
                        **{h.name: None for h in self._read_headers},
                        **dict(zip(worksheet_header_names, row)),
                    },
                    worksheet,
                    row_index + 1,
                )

    def _process_download(
        self,
        data: Iterator[T],
        temp_file: NamedTemporaryFile,
        sheet_name: str = "Export",
        filename: str = "export.xlsx",
    ) -> FileResponse:
        # set up workbook
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name

        # Write data to worksheet, save workbook and return file response
        self._write_worksheet(worksheet, data)
        workbook.save(temp_file.name)
        return FileResponse(temp_file.name, filename=filename)

    def _process_upload(
        self,
        upload_file: UploadFile,
        temp_file: NamedTemporaryFile,
    ) -> Iterator[T]:
        # Save uploaded file to temp file
        shutil.copyfileobj(upload_file.file, temp_file.file)

        # carefully open the Excel file
        try:
            workbook = load_workbook(temp_file.name, read_only=True)
        except Exception:
            # have to catch all exceptions, because openpyxl does raise several
            # exceptions when reading an invalid Excel file
            raise errors.ValueHttpError("Excel file seems to be corrupted")

        # Load data from workbook
        worksheet = workbook.active
        return self._read_worksheet(worksheet)


@cbv(router)
class MeasuresExcelView(ExcelView):
    kwargs = MeasuresView.kwargs

    def __init__(
        self,
        session: Session = Depends(get_session),
        jira_issues: JiraIssuesView = Depends(JiraIssuesView),
        measures: MeasuresView = Depends(MeasuresView),
    ):
        ExcelView.__init__(
            self,
            [
                ExcelHeader("Requirement Reference", ExcelHeader.WRITE_ONLY, True),
                ExcelHeader("Requirement GS ID", ExcelHeader.WRITE_ONLY, True),
                ExcelHeader("Requirement Summary", ExcelHeader.WRITE_ONLY, True),
                ExcelHeader("ID", ExcelHeader.WRITE_ONLY, True),
                ExcelHeader("Summary"),
                ExcelHeader("Description", optional=True),
                ExcelHeader("Completed", optional=True),
                ExcelHeader("Document Reference", ExcelHeader.WRITE_ONLY, True),
                ExcelHeader("Document Title", ExcelHeader.WRITE_ONLY, True),
                ExcelHeader("JIRA Issue Key", ExcelHeader.WRITE_ONLY, True),
            ],
        )
        self._session = session
        self._jira_issues = jira_issues
        self._measures = measures

    def _query_measure_data(
        self, *whereclause: Any
    ) -> Iterator[tuple[Measure, Requirement, Document, JiraIssue]]:
        query = (
            select(Measure, Requirement, Document)
            .join(Requirement)
            .join(Document, isouter=True)
            .where(*whereclause)
            .order_by(Measure.id)
        )
        results = self._session.exec(query).all()

        # query jira issues
        jira_issue_ids = [m.jira_issue_id for m, _, _ in results if m.jira_issue_id]
        jira_issues = self._jira_issues.get_jira_issues(jira_issue_ids)
        jira_issue_map = {ji.id: ji for ji in jira_issues}

        # assign jira issue to measure and yield results
        for measure, requirement, document in results:
            try:
                jira_issue = jira_issue_map[measure.jira_issue_id]
            except KeyError:
                jira_issue = None
            yield measure, requirement, document, jira_issue

    def _convert_to_row(
        self, data: tuple[Measure, Requirement, Document, JiraIssue]
    ) -> dict[str, str]:
        measure, requirement, document, jira_issue = data
        return {
            "Requirement Reference": requirement.reference,
            "Requirement GS ID": requirement.gs_anforderung_reference,
            "Requirement Summary": requirement.summary,
            "ID": measure.id,
            "Summary": measure.summary,
            "Description": measure.description,
            "Completed": measure.completed,
            "Document Reference": document.reference if document else None,
            "Document Title": document.title if document else None,
            "JIRA Issue Key": jira_issue.key if jira_issue else None,
        }

    def _convert_from_row(self, row: dict[str, str], worksheet, row_no) -> MeasureInput:
        try:
            # TODO: validate ID and completed
            return MeasureInput(
                summary=row["Summary"],
                description=row["Description"] or None,
                completed=row["Completed"] or False,
            )
        except ValidationError as error:
            detail = 'Invalid data on worksheet "%s" at row %d: %s' % (
                worksheet.title,
                row_no + 1,
                error,
            )
            raise errors.ValueHttpError(detail)

    @router.get(
        "/projects/{project_id}/measures/excel", response_class=FileResponse, **kwargs
    )
    def download_measures_excel_for_project(
        self,
        project_id: int,
        sheet_name: str = "Export",
        filename: str = "export.xlsx",
        temp_file: NamedTemporaryFile = Depends(get_excel_temp_file),
    ) -> FileResponse:
        return self._process_download(
            self._query_measure_data(Requirement.project_id == project_id),
            temp_file,
            sheet_name,
            filename,
        )

    @router.get(
        "/requirements/{requirement_id}/measures/excel",
        response_class=FileResponse,
        **kwargs,
    )
    def download_measures_excel_for_requirement(
        self,
        requirement_id: int,
        sheet_name: str = "Export",
        filename: str = "export.xlsx",
        temp_file: NamedTemporaryFile = Depends(get_excel_temp_file),
    ) -> FileResponse:
        return self._process_download(
            self._query_measure_data(Requirement.id == requirement_id),
            temp_file,
            sheet_name,
            filename,
        )

    @router.post(
        "/requirements/{requirement_id}/measures/excel",
        status_code=201,
        response_class=Response,
        **kwargs,
    )
    def upload_measures_excel(
        self,
        requirement_id: int,
        upload_file: UploadFile,
        temp_file: NamedTemporaryFile = Depends(get_excel_temp_file),
    ):
        for measure_input in self._process_upload(upload_file, temp_file):
            self._measures.create_measure(requirement_id, measure_input)


@cbv(router)
class ExportRequirementsView(ExcelView):
    kwargs = RequirementsView.kwargs

    def __init__(self, requirements: RequirementsView = Depends(RequirementsView)):
        ExcelView.__init__(
            self,
            [
                "Reference",
                "Summary",
                "Description",
                "Target Object",
                "Compliance Status",
                "Compliance Comment",
                "Completion",
            ],
        )
        self._requirements = requirements

    def _convert_to_row(self, data: Requirement) -> dict[str, str]:
        return {
            "Reference": data.reference,
            "Summary": data.summary,
            "Description": data.description,
            "Target Object": data.target_object,
            "Compliance Status": data.compliance_status,
            "Compliance Comment": data.compliance_comment,
            "Completion": data.completion,
        }

    @router.get(
        "/projects/{project_id}/requirements/excel",
        response_class=FileResponse,
        **kwargs,
    )
    def download_requirements_excel(
        self,
        project_id: int,
        sheet_name: str = "Export",
        filename: str = "export.xlsx",
        temp_file: NamedTemporaryFile = Depends(get_excel_temp_file),
    ) -> FileResponse:
        return self._process_download(
            self._requirements.list_requirements(project_id),
            temp_file,
            sheet_name,
            filename,
        )


@cbv(router)
class ExportDocumentsView(ExcelView):
    kwargs = DocumentsView.kwargs

    def __init__(self, documents: DocumentsView = Depends(DocumentsView)):
        ExcelView.__init__(self, ["ID", "Reference", "Title", "Description"])
        self._documents = documents

    def _convert_documents_to_dict(
        self, documents: Iterator[Document]
    ) -> Iterator[dict[str, str]]:
        for document in documents:
            yield {
                "ID": document.id,
                "Reference": document.reference,
                "Title": document.title,
                "Description": document.description,
            }

    def _convert_to_row(self, data: Document) -> dict[str, str]:
        return {
            "ID": data.id,
            "Reference": data.reference,
            "Title": data.title,
            "Description": data.description,
        }

    @router.get(
        "/projects/{project_id}/documents/excel",
        response_class=FileResponse,
        **kwargs,
    )
    def download_documents_excel(
        self,
        project_id: int,
        sheet_name: str = "Export",
        filename: str = "export.xlsx",
        temp_file: NamedTemporaryFile = Depends(get_excel_temp_file),
    ) -> FileResponse:
        return self._process_download(
            self._documents.list_documents(project_id),
            temp_file,
            sheet_name,
            filename,
        )


@cbv(router)
class ImportRequirementsView(ExcelView):
    kwargs = dict(tags=["requirement"])

    def __init__(
        self,
        requirements: RequirementsView = Depends(RequirementsView),
    ):
        ExcelView.__init__(
            self,
            [
                "Reference",
                "Summary",
                "Description",
                "Target Object",
                "Compliance Status",
                "Compliance Comment",
            ],
        )
        self._requirements = requirements

    def _convert_from_row(
        self, row: dict[str, str], worksheet, row_no
    ) -> RequirementInput:
        try:
            return RequirementInput(
                reference=row["Reference"],
                summary=row["Summary"],
                description=row["Description"],
                target_object=row["Target Object"],
                compliance_status=row["Compliance Status"],
                compliance_comment=row["Compliance Comment"],
            )
        except ValidationError as error:
            detail = 'Invalid data on worksheet "%s" at row %d: %s' % (
                worksheet.title,
                row_no + 1,
                error,
            )
            raise errors.ValueHttpError(detail)

    @router.post(
        "/projects/{project_id}/requirements/excel",
        status_code=201,
        response_class=Response,
        **kwargs,
    )
    def upload_requirements_excel(
        self,
        project_id: int,
        upload_file: UploadFile,
        temp_file: NamedTemporaryFile = Depends(get_excel_temp_file),
    ):
        for requirement_input in self._process_upload(upload_file, temp_file):
            self._requirements.create_requirement(project_id, requirement_input)


# @cbv(router)
# class ImportMeasuresView(ExcelView):
#     kwargs = MeasuresView.kwargs

#     def __init__(self, measures: MeasuresView = Depends(MeasuresView)):
#         ExcelView.__init__(self, ["Summary", "Description"])
#         self._measures = measures

#     def _convert_from_row(self, row: dict[str, str], worksheet, row_no) -> MeasureInput:
#         try:
#             return MeasureInput(
#                 summary=row["Summary"],
#                 description=row["Description"] or None,
#             )
#         except ValidationError as error:
#             detail = 'Invalid data on worksheet "%s" at row %d: %s' % (
#                 worksheet.title,
#                 row_no + 1,
#                 error,
#             )
#             raise errors.ValueHttpError(detail)

#     @router.post(
#         "/requirements/{requirement_id}/measures/excel",
#         status_code=201,
#         response_class=Response,
#         **kwargs,
#     )
#     def upload_measures_excel(
#         self,
#         requirement_id: int,
#         upload_file: UploadFile,
#         temp_file: NamedTemporaryFile = Depends(get_excel_temp_file),
#     ):
#         for measure_input in self._process_upload(upload_file, temp_file):
#             self._measures.create_measure(requirement_id, measure_input)


@cbv(router)
class ImportDocumentsView(ExcelView):
    kwargs = DocumentsView.kwargs

    def __init__(self, documents: DocumentsView = Depends(DocumentsView)):
        ExcelView.__init__(self, ["Reference", "Title", "Description"])
        self._documents = documents

    def _convert_from_row(
        self, row: dict[str, str], worksheet, row_no
    ) -> DocumentInput:
        try:
            return DocumentInput(
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

    @router.post(
        "/projects/{project_id}/documents/excel",
        status_code=201,
        response_class=Response,
        **kwargs,
    )
    def upload_documents_excel(
        self,
        project_id: int,
        upload_file: UploadFile,
        temp_file: NamedTemporaryFile = Depends(get_excel_temp_file),
    ):
        for document_input in self._process_upload(upload_file, temp_file):
            self._documents.create_document(project_id, document_input)
