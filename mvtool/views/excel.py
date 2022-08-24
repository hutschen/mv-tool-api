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


from tempfile import NamedTemporaryFile
from typing import Any, Collection, Dict
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
        return temp_file


router = APIRouter()


class ExcelMixin:
    def _write_worksheet(
        self,
        worksheet: Worksheet,
        headers: Collection[str],
        data: Iterator[dict[str, str]],
    ):
        # Fill worksheet with data
        worksheet.append(headers)
        is_empty = True
        for row in data:
            values = [row.get(header, "") for header in headers]
            worksheet.append(values)
            is_empty = False

        # Add table to worksheet
        if not is_empty:
            table = Table(
                displayName=worksheet.title, ref=worksheet.calculate_dimension()
            )
            worksheet.add_table(table)

    def _read_worksheet(
        self, worksheet: Worksheet, headers: Collection[str]
    ) -> Iterator[Dict[str, str]]:
        headers = set(headers)
        is_header_row = True

        for row in worksheet.iter_rows(values_only=True):
            if is_header_row:
                # Check if all headers are present
                if not headers.issubset(row):
                    detail = 'Missing headers on worksheet "%s": %s' % (
                        worksheet.title,
                        ", ".join(headers - set(row)),
                    )
                    raise errors.ValueHttpError(detail)
                headers = tuple(row)
                is_header_row = False
            else:
                # Convert row to dict and yield
                yield dict(zip(headers, row))


@cbv(router)
class ExportMeasuresView(ExcelMixin):
    kwargs = dict(tags=["measure"])

    def __init__(
        self,
        session: Session = Depends(get_session),
        jira_issues: JiraIssuesView = Depends(JiraIssuesView),
    ):
        self._session = session
        self._jira_issues = jira_issues
        self._headers = [
            "Requirement Reference",
            "Requirement Summary",
            "Summary",
            "Description",
            "Completed",
            "Document Reference",
            "Document Title",
            "JIRA Issue Key",
        ]

    def _query_measure_data(
        self, *whereclause: Any
    ) -> Iterator[tuple[Measure, Requirement, Document, JiraIssue]]:
        query = (
            select(Measure, Requirement, Document)
            .join(Requirement)
            .join(Document, isouter=True)
            .where(*whereclause)
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

    def _convert_measure_data_to_dict(
        self, data: Iterator[tuple[Measure, Requirement, Document, JiraIssue]]
    ) -> Iterator[dict[str, str]]:
        for measure, requirement, document, jira_issue in data:
            yield {
                "Requirement Reference": requirement.reference,
                "Requirement Summary": requirement.summary,
                "Summary": measure.summary,
                "Description": measure.description,
                "Completed": measure.completed,
                "Document Reference": document.reference if document else "",
                "Document Title": document.title if document else "",
                "JIRA Issue Key": jira_issue.key if jira_issue else "",
            }

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
        # set up workbook
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name

        # query and write measure data
        data = self._query_measure_data(Requirement.project_id == project_id)
        rows = self._convert_measure_data_to_dict(data)
        self._write_worksheet(worksheet, self._headers, rows)

        # save to temporary file and return file response
        workbook.save(temp_file.name)
        return FileResponse(temp_file.name, filename=filename)

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
        # set up workbook
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name

        # query measure data
        data = self._query_measure_data(Measure.requirement_id == requirement_id)
        rows = self._convert_measure_data_to_dict(data)
        self._write_worksheet(worksheet, self._headers, rows)

        # save to temporary file and return file response
        workbook.save(temp_file.name)
        return FileResponse(temp_file.name, filename=filename)


@cbv(router)
class ExportRequirementsView(ExcelMixin):
    kwargs = dict(tags=["requirement"])

    def __init__(self, requirements: RequirementsView = Depends(RequirementsView)):
        self._requirements = requirements
        self._headers = [
            "Reference",
            "Summary",
            "Description",
            "Target Object",
            "Compliance Status",
            "Compliance Comment",
            "Completion",
        ]

    def _convert_requirements_to_dict(
        self, requirements: Iterator[Requirement]
    ) -> Iterator[dict[str, str]]:
        for requirement in requirements:
            yield {
                "Reference": requirement.reference,
                "Summary": requirement.summary,
                "Description": requirement.description,
                "Target Object": requirement.target_object,
                "Compliance Status": requirement.compliance_status,
                "Compliance Comment": requirement.compliance_comment,
                "Completion": requirement.completion,
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
        # set up workbook
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name

        # fill worksheet with data
        requirements = self._requirements.list_requirements(project_id)
        rows = self._convert_requirements_to_dict(requirements)
        self._write_worksheet(worksheet, self._headers, rows)

        # save to temporary file and return response
        workbook.save(temp_file.name)
        return FileResponse(temp_file.name, filename=filename)


@cbv(router)
class ExportDocumentsView:
    kwargs = dict(tags=["document"])

    def __init__(self, documents: DocumentsView = Depends(DocumentsView)):
        self._documents = documents

    def fill_excel_worksheet_with_document_data(
        self, worksheet: Worksheet, project_id: int
    ) -> None:
        worksheet.append(["ID", "Reference", "Title", "Description"])

        is_empty = True
        for document in self._documents.list_documents(project_id):
            worksheet.append(
                [document.id, document.reference, document.title, document.description]
            )
            is_empty = False

        if not is_empty:
            table = Table(
                displayName=worksheet.title, ref=worksheet.calculate_dimension()
            )
            worksheet.add_table(table)

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
        # set up workbook
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name

        # fill worksheet with data
        self.fill_excel_worksheet_with_document_data(worksheet, project_id)

        # save to temporary file and return response
        workbook.save(temp_file.name)
        return FileResponse(temp_file.name, filename=filename)


class ImportExcelView:
    def _upload_to_workbook(
        self,
        upload_file: UploadFile,
        temp_file: NamedTemporaryFile = Depends(get_excel_temp_file),
    ) -> Workbook:
        with open(temp_file.name, "wb") as f:
            # 1MB buffer size should be sufficient to load an Excel file
            buffer_size = 1000 * 1024
            chunk = upload_file.file.read(buffer_size)
            while chunk:
                f.write(chunk)
                chunk = upload_file.file.read(buffer_size)

        # carefully open the Excel file
        try:
            return load_workbook(temp_file.name, read_only=True)
        except Exception:
            # have to catch all exceptions, because openpyxl does raise several
            # exceptions when reading an invalid Excel file
            raise errors.ValueHttpError("Excel file seems to be corrupt")

    def _iter_rows_on_worksheet(
        self, worksheet: Worksheet, headers: Collection[str]
    ) -> Iterator[Dict[str, str]]:
        headers = set(headers)
        is_header_row = True

        for row in worksheet.iter_rows(values_only=True):
            if is_header_row:
                # check if all required headers are present
                if not headers.issubset(row):
                    detail = 'Missing headers on worksheet "%s": %s' % (
                        worksheet.title,
                        ", ".join(headers - set(row)),
                    )
                    raise errors.ValueHttpError(detail)
                headers = tuple(row)
                is_header_row = False
            else:
                yield dict(zip(headers, row))


@cbv(router)
class ImportRequirementsView(ImportExcelView):
    kwargs = dict(tags=["requirement"])

    def __init__(
        self,
        requirements: RequirementsView = Depends(RequirementsView),
    ):
        self._requirements = requirements

    def read_requirement_from_excel_worksheet(self, worksheet: Worksheet):
        for index, row in enumerate(
            self._iter_rows_on_worksheet(
                worksheet,
                (
                    "Reference",
                    "Summary",
                    "Description",
                    "Target Object",
                    "Compliance Status",
                    "Compliance Comment",
                ),
            )
        ):
            try:
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
                    index + 1,
                    error,
                )
                raise errors.ValueHttpError(detail)
            else:
                yield requirement_input

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
        # get worksheet from Excel file
        workbook = self._upload_to_workbook(upload_file, temp_file)
        worksheet = workbook.active

        # read data from worksheet
        for requirement_input in self.read_requirement_from_excel_worksheet(worksheet):
            self._requirements.create_requirement(project_id, requirement_input)


@cbv(router)
class ImportMeasuresView(ImportExcelView):
    kwargs = dict(tags=["measure"])

    def __init__(self, measures: MeasuresView = Depends(MeasuresView)):
        self._measures = measures

    def read_measures_from_excel_worksheet(self, worksheet: Worksheet):
        for index, row in enumerate(
            self._iter_rows_on_worksheet(
                worksheet,
                ("Summary", "Description"),
            )
        ):
            try:
                measure_input = MeasureInput(
                    summary=row["Summary"],
                    description=row["Description"] or None,
                )
            except ValidationError as error:
                detail = 'Invalid data on worksheet "%s" at row %d: %s' % (
                    worksheet.title,
                    index + 1,
                    error,
                )
                raise errors.ValueHttpError(detail)
            else:
                yield measure_input
            try:
                measure_input = MeasureInput(
                    summary=row["Summary"],
                    description=row["Description"] or None,
                )
            except ValidationError as error:
                detail = 'Invalid data on worksheet "%s" at row %d: %s' % (
                    worksheet.title,
                    index + 1,
                    error,
                )
                raise errors.ValueHttpError(detail)
            else:
                yield measure_input

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
        # get worksheet from Excel file
        workbook = self._upload_to_workbook(upload_file, temp_file)
        worksheet = workbook.active

        # read measures from worksheet
        for measure_input in self.read_measures_from_excel_worksheet(worksheet):
            self._measures.create_measure(requirement_id, measure_input)


@cbv(router)
class ImportDocumentsView(ImportExcelView):
    kwargs = dict(tags=["document"])

    def __init__(self, documents: DocumentsView = Depends(DocumentsView)):
        self._documents = documents

    def read_documents_from_excel_worksheet(self, worksheet: Worksheet):
        for index, row in enumerate(
            self._iter_rows_on_worksheet(
                worksheet,
                ("Reference", "Title", "Description"),
            )
        ):
            try:
                document_input = DocumentInput(
                    reference=row["Reference"] or None,
                    title=row["Title"],
                    description=row["Description"] or None,
                )
            except ValidationError as error:
                detail = 'Invalid data on worksheet "%s" at row %d: %s' % (
                    worksheet.title,
                    index + 1,
                    error,
                )
                raise errors.ValueHttpError(detail)
            else:
                yield document_input

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
        # get worksheet from Excel file
        workbook = self._upload_to_workbook(upload_file, temp_file)
        worksheet = workbook.active

        # read documents from worksheet
        for document_input in self.read_documents_from_excel_worksheet(worksheet):
            self._documents.create_document(project_id, document_input)
