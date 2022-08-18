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
from mvtool.models import Document, Measure, MeasureInput, Requirement, RequirementInput
from mvtool.views.jira_ import JiraIssuesView
from mvtool.views.measures import MeasuresView
from mvtool.views.requirements import RequirementsView


def get_excel_temp_file():
    with NamedTemporaryFile(suffix=".xlsx") as temp_file:
        return temp_file


router = APIRouter()


@cbv(router)
class ExportMeasuresView:
    kwargs = dict(tags=["measure"])

    def __init__(
        self,
        session: Session = Depends(get_session),
        jira_issues: JiraIssuesView = Depends(JiraIssuesView),
    ):
        self._session = session
        self._jira_issues = jira_issues

    def _query_measure_data(self, *whereclause: Any) -> Iterator:
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

    def _fill_excel_worksheet_with_measure_data(
        self, worksheet: Worksheet, measure_data
    ):
        worksheet.append(
            [
                "Requirement Reference",
                "Requirement Summary",
                "Summary",
                "Description",
                "Completed",
                "Document Reference",
                "Document Title",
                "JIRA Issue Key",
            ]
        )

        is_empty = True
        for measure, requirement, document, jira_issue in measure_data:
            worksheet.append(
                [
                    requirement.reference,
                    requirement.summary,
                    measure.summary,
                    measure.description,
                    measure.completed,
                    document.reference if document else "",
                    document.title if document else "",
                    jira_issue.key if jira_issue else "",
                ]
            )
            is_empty = False

        if not is_empty:
            table = Table(
                displayName=worksheet.title, ref=worksheet.calculate_dimension()
            )
            worksheet.add_table(table)

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

        # query measure data
        measure_data = self._query_measure_data(Requirement.project_id == project_id)
        self._fill_excel_worksheet_with_measure_data(worksheet, measure_data)

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
        measure_data = self._query_measure_data(
            Measure.requirement_id == requirement_id
        )
        self._fill_excel_worksheet_with_measure_data(worksheet, measure_data)

        # save to temporary file and return file response
        workbook.save(temp_file.name)
        return FileResponse(temp_file.name, filename=filename)


@cbv(router)
class ExportRequirementsView:
    kwargs = dict(tags=["requirement"])

    def __init__(self, requirements: RequirementsView = Depends(RequirementsView)):
        self._requirements = requirements

    def fill_excel_worksheet_with_requirement_data(
        self, worksheet: Worksheet, project_id: int
    ) -> None:
        worksheet.append(
            [
                "Reference",
                "Summary",
                "Description",
                "Target Object",
                "Compliance Status",
                "Compliance Comment",
                "Completion",
            ]
        )

        is_empty = True
        for requirement in self._requirements.list_requirements(project_id):
            worksheet.append(
                [
                    requirement.reference,
                    requirement.summary,
                    requirement.description,
                    requirement.target_object,
                    requirement.compliance_status,
                    requirement.compliance_comment,
                    requirement.completion,
                ]
            )
            is_empty = False

        if not is_empty:
            table = Table(
                displayName=worksheet.title, ref=worksheet.calculate_dimension()
            )
            worksheet.add_table(table)

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
        self.fill_excel_worksheet_with_requirement_data(worksheet, project_id)

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
