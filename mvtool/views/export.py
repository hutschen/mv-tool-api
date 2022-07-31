# coding: utf-8
# 
# Copyright 2022 Helmar Hutschenreuter
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation. You may obtain
# a copy of the GNU AGPL V3 at https://www.gnu.org/licenses/.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AGPL V3 for more details.

from tempfile import NamedTemporaryFile
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from fastapi_utils.cbv import cbv
from pyparsing import Iterator
from sqlmodel import Session, select
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl import Workbook
from openpyxl.worksheet.table import Table

from mvtool.database import get_session
from mvtool.models import Document, Measure, Requirement
from mvtool.views.jira_ import JiraIssuesView
from mvtool.views.requirements import RequirementsView

def get_excel_temp_file():
    with NamedTemporaryFile(suffix='.xlsx') as temp_file:
        return temp_file

router = APIRouter()

@cbv(router)
class ExportMeasuresView:
    kwargs = dict(tags=['measure'])

    def __init__(self, 
            session: Session = Depends(get_session), 
            jira_issues: JiraIssuesView = Depends(JiraIssuesView)):
        self._session = session
        self._jira_issues = jira_issues

    def query_measure_data(self, project_id: int) -> Iterator:
        query = select(Measure, Requirement, Document).where(
            Measure.requirement_id == Requirement.id,
            Measure.document_id == Document.id,
            Requirement.project_id == project_id)
        results = self._session.exec(query).all()

        # query jira issues
        jira_issue_ids = [
            m.jira_issue_id for m, _, _ in results if m.jira_issue_id]
        jira_issues = self._jira_issues.get_jira_issues(jira_issue_ids)
        jira_issue_map = {ji.id:ji for ji in jira_issues}

        # assign jira issue to measure and yield results
        for measure, requirement, document in results:
            try:
                jira_issue = jira_issue_map[measure.jira_issue_id]
            except KeyError:
                jira_issue = None
            yield measure, requirement, document, jira_issue

    def fill_excel_worksheet_with_measure_data(
            self, worksheet: Worksheet, project_id: int):
        worksheet.append([
            'Requirement Reference', 'Requirement Summary', 'Summary', 
            'Description', 'Completed', 'Document Reference', 'Document Title', 
            'JIRA Issue Key'])

        for measure, requirement, document, jira_issue \
                in self.query_measure_data(project_id):
            worksheet.append([
                requirement.reference, requirement.summary, measure.summary, 
                measure.description, measure.completed, 
                document.reference if document else '', 
                document.title if document else '', 
                jira_issue.key if jira_issue else ''])
        
        table = Table(
            displayName=worksheet.title, ref=worksheet.calculate_dimension())
        worksheet.add_table(table)

    @router.get(
        '/projects/{project_id}/measures/excel', 
        response_class=FileResponse, **kwargs)
    def download_measures_excel(
            self, project_id: int, sheet_name: str='Export', 
            filename: str='export.xlsx', 
            temp_file: NamedTemporaryFile = Depends(get_excel_temp_file)
        ) -> FileResponse:
        # set up workbook
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name

        # fill worksheet
        self.fill_excel_worksheet_with_measure_data(worksheet, project_id)

        # save to temporary file and return file response
        workbook.save(temp_file.name)
        return FileResponse(temp_file.name, filename=filename)


@cbv(router)
class ExportRequirementsView:
    kwargs = dict(tags=['requirement'])

    def __init__(
            self, requirements: RequirementsView = Depends(RequirementsView)):
        self._requirements = requirements

    def fill_excel_worksheet_with_requirement_data(
            self, worksheet: Worksheet, project_id: int) -> None:
        worksheet.append([
            'Reference', 'Summary', 'Description', 'Target Object', 
            'Compliance Status', 'Compliance Comment', 'Completion'])

        for requirement in self._requirements.list_requirements(project_id):
            worksheet.append([
                requirement.reference, requirement.summary, 
                requirement.description, requirement.target_object,
                requirement.compliance_status, requirement.compliance_comment,
                requirement.completion
            ])

        table = Table(
            displayName=worksheet.title, ref=worksheet.calculate_dimension())
        worksheet.add_table(table)

    @router.get(
        '/projects/{project_id}/requirements/excel', 
        response_class=FileResponse, **kwargs)
    def download_requirements_excel(
            self, project_id: int, sheet_name: str='Export', 
            filename: str ='export.xlsx',
            temp_file: NamedTemporaryFile = Depends(get_excel_temp_file)
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
