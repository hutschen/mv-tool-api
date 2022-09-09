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
from pydantic import ValidationError, BaseModel
from pyparsing import Iterator
from sqlmodel import Session, select
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.table import Table

from mvtool import errors
from mvtool.database import get_session
from mvtool.models import (
    Document,
    DocumentOutput,
    JiraIssue,
    Measure,
    MeasureInput,
    MeasureOutput,
    Requirement,
    RequirementInput,
    DocumentInput,
    RequirementOutput,
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


class IdModel(BaseModel):
    id: int | None


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

    def _convert_to_row(self, data: T, *args) -> dict[str, str]:
        raise NotImplementedError("Must be implemented by subclass")

    def _write_worksheet(
        self,
        worksheet: Worksheet,
        data: Iterator[T],
        *args,
    ):
        header_names = set()
        rows = []

        # Convert data to rows and determine headers
        for row_data in data:
            row = self._convert_to_row(row_data, *args)
            for header in self._write_headers:
                if header.optional and not row[header.name]:
                    continue
                header_names.add(header.name)
            rows.append(row)

        # Arrange headers in the order they are defined
        header_names = [h.name for h in self._write_headers if h.name in header_names]

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

    def _convert_from_row(self, row: dict[str, str], worksheet, row_no, *args) -> T:
        raise NotImplementedError("Must be implemented by subclass")

    def _read_worksheet(self, worksheet: Worksheet, *args) -> Iterator[T]:
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
                    *args,
                )

    def _process_download(
        self,
        data: Iterator[T],
        temp_file: NamedTemporaryFile,
        *args,
        sheet_name: str = "Export",
        filename: str = "export.xlsx",
    ) -> FileResponse:
        # set up workbook
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name

        # Write data to worksheet, save workbook and return file response
        self._write_worksheet(worksheet, data, *args)
        workbook.save(temp_file.name)
        return FileResponse(temp_file.name, filename=filename)

    def _process_upload(
        self, upload_file: UploadFile, temp_file: NamedTemporaryFile, *args
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
        return self._read_worksheet(worksheet, *args)


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
                ExcelHeader("ID", optional=True),
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
        self, data: tuple[Measure, Requirement, Document, JiraIssue], *args
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

    def _convert_from_row(
        self, row: dict[str, str], worksheet, row_no: int, requirement_id: int
    ) -> MeasureInput:
        try:
            measure_id = IdModel(id=row["ID"]).id
            measure_input = MeasureInput(
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

        # Create of update measure
        if measure_id is None:
            return self._measures.create_measure(requirement_id, measure_input)
        else:
            # FIXME: Check if measure belongs to requirement
            return self._measures.update_measure(measure_id, measure_input)

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
            sheet_name=sheet_name,
            filename=filename,
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
            sheet_name=sheet_name,
            filename=filename,
        )

    @router.post(
        "/requirements/{requirement_id}/measures/excel",
        status_code=201,
        response_model=list[MeasureOutput],
        **kwargs,
    )
    def upload_measures_excel(
        self,
        requirement_id: int,
        upload_file: UploadFile,
        temp_file: NamedTemporaryFile = Depends(get_excel_temp_file),
    ) -> Iterator[MeasureOutput]:
        return self._process_upload(upload_file, temp_file, requirement_id)


@cbv(router)
class RequirementsExcelView(ExcelView):
    kwargs = RequirementsView.kwargs

    def __init__(self, requirements: RequirementsView = Depends(RequirementsView)):
        ExcelView.__init__(
            self,
            [
                ExcelHeader("ID", optional=True),
                ExcelHeader("Reference", optional=True),
                ExcelHeader("GS ID", ExcelHeader.WRITE_ONLY, True),
                ExcelHeader("GS Baustein", ExcelHeader.WRITE_ONLY, True),
                ExcelHeader("Summary"),
                ExcelHeader("Description", optional=True),
                ExcelHeader("GS Absicherung", ExcelHeader.WRITE_ONLY, True),
                ExcelHeader("GS Verantwortliche", ExcelHeader.WRITE_ONLY, True),
                ExcelHeader("Target Object", optional=True),
                ExcelHeader("Compliance Status", optional=True),
                ExcelHeader("Compliance Comment", optional=True),
                ExcelHeader("Completion", ExcelHeader.WRITE_ONLY, True),
            ],
        )
        self._requirements = requirements

    def _convert_to_row(self, data: Requirement) -> dict[str, str]:
        return {
            "ID": data.id,
            "Reference": data.reference,
            "GS ID": data.gs_anforderung_reference,
            "GS Baustein": data.gs_baustein.title if data.gs_baustein else None,
            "Summary": data.summary,
            "Description": data.description,
            "GS Absicherung": data.gs_absicherung,
            "GS Verantwortliche": data.gs_verantwortliche,
            "Target Object": data.target_object,
            "Compliance Status": data.compliance_status,
            "Compliance Comment": data.compliance_comment,
            "Completion": data.completion,
        }

    def _convert_from_row(
        self, row: dict[str, str], worksheet, row_no: int, project_id: int
    ) -> RequirementInput:
        try:
            requirement_id = IdModel(id=row["ID"]).id
            requirement_input = RequirementInput(
                reference=row["Reference"] or None,
                summary=row["Summary"],
                description=row["Description"] or None,
                target_object=row["Target Object"] or None,
                compliance_status=row["Compliance Status"] or None,
                compliance_comment=row["Compliance Comment"] or None,
            )
        except ValidationError as error:
            detail = 'Invalid data on worksheet "%s" at row %d: %s' % (
                worksheet.title,
                row_no + 1,
                error,
            )
            raise errors.ValueHttpError(detail)

        # Create or update requirement
        if requirement_id is None:
            return self._requirements._create_requirement(project_id, requirement_input)
        else:
            # FIXME: Check if requirement belongs to project
            return self._requirements._update_requirement(
                requirement_id, requirement_input
            )

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
            sheet_name=sheet_name,
            filename=filename,
        )

    @router.post(
        "/projects/{project_id}/requirements/excel",
        status_code=201,
        response_model=list[RequirementOutput],
        **kwargs,
    )
    def upload_requirements_excel(
        self,
        project_id: int,
        upload_file: UploadFile,
        temp_file: NamedTemporaryFile = Depends(get_excel_temp_file),
    ) -> Iterator[RequirementOutput]:
        return self._process_upload(upload_file, temp_file, project_id)


@cbv(router)
class DocumentsExcelView(ExcelView):
    kwargs = DocumentsView.kwargs

    def __init__(self, documents: DocumentsView = Depends(DocumentsView)):
        ExcelView.__init__(
            self,
            [
                ExcelHeader("ID", optional=True),
                ExcelHeader("Reference", optional=True),
                ExcelHeader("Title"),
                ExcelHeader("Description", optional=True),
            ],
        )
        self._documents = documents

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
            sheet_name=sheet_name,
            filename=filename,
        )

    def _convert_from_row(
        self, row: dict[str, str], worksheet, row_no: int, project_id: int
    ) -> DocumentOutput:
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

        # Create or update the document
        if document_id is None:
            return self._documents._create_document(project_id, document_input)
        else:
            # FIXME: Check if the document belongs to the project
            return self._documents._update_document(document_id, document_input)

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
    ) -> Iterator[DocumentOutput]:
        return self._process_upload(upload_file, temp_file, project_id)
