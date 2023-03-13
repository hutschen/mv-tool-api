# conding: utf-8
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
from typing import Any, Iterator

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse
from fastapi_utils.cbv import cbv
from pydantic import ValidationError
from sqlmodel import Session, select

from ... import errors
from ...database import get_session
from ...models import Measure, MeasureInput, MeasureOutput
from ...utils.temp_file import get_temp_file
from ..jira_ import JiraIssuesView
from ..measures import MeasuresView, get_measure_filters, get_measure_sort
from .common import ExcelHeader, ExcelView, IdModel, JiraIssueKeyModel
from .documents import convert_document_to_row, get_document_excel_headers_only
from .requirements import convert_requirement_to_row, get_requirement_excel_headers

router = APIRouter()


def get_measure_excel_headers(
    requirement_headers=Depends(get_requirement_excel_headers),
    document_headers=Depends(get_document_excel_headers_only),
) -> list[ExcelHeader]:
    return [
        *requirement_headers,
        ExcelHeader("Measure ID", optional=True),
        ExcelHeader("Measure Reference", optional=True),
        ExcelHeader("Measure Summary"),
        ExcelHeader("Measure Description", optional=True),
        ExcelHeader("Measure Compliance Status", optional=True),
        ExcelHeader("Measure Compliance Comment", optional=True),
        ExcelHeader("Measure Completion Status", optional=True),
        ExcelHeader("Measure Completion Comment", optional=True),
        ExcelHeader("Measure Verification Method", optional=True),
        ExcelHeader("Measure Verification Status", optional=True),
        ExcelHeader("Measure Verification Comment", optional=True),
        ExcelHeader("JIRA Issue Key", optional=True),
        *document_headers,
    ]


def convert_measure_to_row(measure: Measure) -> dict[str, Any]:
    return {
        **convert_requirement_to_row(measure.requirement),
        "Measure ID": measure.id,
        "Measure Reference": measure.reference,
        "Measure Summary": measure.summary,
        "Measure Description": measure.description,
        "Measure Compliance Status": measure.compliance_status,
        "Measure Compliance Comment": measure.compliance_comment,
        "Measure Completion Status": measure.completion_status,
        "Measure Completion Comment": measure.completion_comment,
        "Measure Verification Method": measure.verification_method,
        "Measure Verification Status": measure.verification_status,
        "Measure Verification Comment": measure.verification_comment,
        "JIRA Issue Key": measure.jira_issue.key if measure.jira_issue else None,
        **convert_document_to_row(measure.document, document_only=True),
    }


@cbv(router)
class MeasuresExcelView(ExcelView):
    kwargs = dict(tags=["excel"])

    def __init__(
        self,
        session: Session = Depends(get_session),
        jira_issues: JiraIssuesView = Depends(JiraIssuesView),
        measures: MeasuresView = Depends(MeasuresView),
        headers: list[ExcelHeader] = Depends(get_measure_excel_headers),
    ):
        ExcelView.__init__(self, headers)
        self._session = session
        self._jira_issues = jira_issues
        self._measures = measures

    def _convert_to_row(self, data: Measure, *args) -> dict[str, str]:
        return convert_measure_to_row(data)

    @router.get(
        "/excel/measures",
        response_class=FileResponse,
        **kwargs,
    )
    def download_measures_excel(
        self,
        where_clauses=Depends(get_measure_filters),
        order_by_clauses=Depends(get_measure_sort),
        temp_file: NamedTemporaryFile = Depends(get_temp_file(".xlsx")),
        sheet_name: str = "Export",
        filename: str = "export.xlsx",
    ) -> FileResponse:
        return self._process_download(
            self._measures.list_measures(where_clauses, order_by_clauses),
            temp_file,
            sheet_name=sheet_name,
            filename=filename,
        )

    def _convert_from_row(
        self, row: dict[str, str], worksheet, row_no: int
    ) -> tuple[int | None, str | None, MeasureInput]:
        try:
            measure_id = IdModel(id=row["ID"]).id
            jira_issue_key = JiraIssueKeyModel(key=row["JIRA Issue Key"]).key
            measure_input = MeasureInput(
                reference=row["Reference"] or None,
                summary=row["Summary"],
                description=row["Description"] or None,
                compliance_status=row["Compliance Status"] or None,
                compliance_comment=row["Compliance Comment"] or None,
                completion_status=row["Completion Status"] or None,
                completion_comment=row["Completion Comment"] or None,
                verification_status=row["Verification Status"] or None,
                verification_method=row["Verification Method"] or None,
                verification_comment=row["Verification Comment"] or None,
            )
        except ValidationError as error:
            detail = 'Invalid data on worksheet "%s" at row %d: %s' % (
                worksheet.title,
                row_no + 1,
                error,
            )
            raise errors.ValueHttpError(detail)
        else:
            return measure_id, jira_issue_key, measure_input

    def _bulk_create_patch_measures(
        self,
        requirement_id: int,
        data: Iterator[tuple[int | None, str | None, MeasureInput]],
    ) -> list[Measure]:
        # TODO: Define this attribute in constructor
        self._requirements = self._measures._requirements
        self._documents = self._measures._documents

        # Get requirement from database and retrieve data
        requirement = self._requirements.get_requirement(requirement_id)
        data = list(data)

        # Read measures to be updated from database
        query = select(Measure).where(
            Measure.id.in_({id for id, _, _ in data if id is not None}),
            Measure.requirement_id == requirement_id,
        )
        read_measures = dict((m.id, m) for m in self._session.exec(query).all())

        # Retrieve jira issues to be linked to measures and
        # jira issues currently linked to measures to cache them
        jira_issues = self._jira_issues.get_jira_issues(
            [ji_key for _, ji_key, _ in data if ji_key]
            + [
                m.jira_issue_id
                for m in read_measures.values()
                if m.jira_issue_id is not None
            ]
        )
        jira_issue_map = {ji.key: ji for ji in jira_issues}

        # Create or update measures
        written_measures = []
        for measure_id, jira_issue_key, measure_input in data:
            jira_issue = None

            # Set jira issue id
            if jira_issue_key:
                jira_issue = jira_issue_map.get(jira_issue_key)
                if jira_issue is None:
                    raise errors.NotFoundError(f"JIRA issue {jira_issue_key} not found")
                measure_input.jira_issue_id = jira_issue.id

            if measure_id is None:
                # Create measure
                measure = Measure.from_orm(measure_input)
                measure.requirement = requirement
            else:
                # Update measure
                measure = read_measures.get(measure_id)
                if measure is None:
                    raise errors.NotFoundError(
                        "Measure with ID %d not part of requirement with ID %d"
                        % (measure_id, requirement_id)
                    )
                for key, value in measure_input.dict(exclude_unset=True).items():
                    setattr(measure, key, value)

            # set jira project and issue
            self._measures._set_jira_project(measure)
            self._measures._set_jira_issue(measure, try_to_get=False)

            # TODO: Checking document id should be done more efficiently
            self._documents.check_document_id(measure.document_id)
            self._session.add(measure)
            written_measures.append(measure)

        self._session.flush()
        return written_measures

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
        temp_file: NamedTemporaryFile = Depends(get_temp_file(".xlsx")),
    ) -> Iterator[MeasureOutput]:
        return self._bulk_create_patch_measures(
            requirement_id, self._process_upload(upload_file, temp_file)
        )
