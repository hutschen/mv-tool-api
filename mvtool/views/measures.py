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

from typing import Iterator
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi_utils.cbv import cbv
from openpyxl.worksheet.table import Table
from sqlmodel import select
from openpyxl.worksheet.worksheet import Worksheet

from mvtool.views.documents import DocumentsView
from mvtool.views.jira_ import JiraIssuesView
from ..database import CRUDOperations
from .requirements import RequirementsView
from ..models import JiraIssue, JiraIssueInput, MeasureInput, Measure, MeasureOutput, Requirement

router = APIRouter()


@cbv(router)
class MeasuresView:
    kwargs = dict(tags=['measure'])

    def __init__(self,
            jira_issues: JiraIssuesView = Depends(JiraIssuesView),
            requirements: RequirementsView = Depends(RequirementsView),
            documents: DocumentsView = Depends(DocumentsView),
            crud: CRUDOperations[Measure] = Depends(CRUDOperations)):
        self._jira_issues = jira_issues
        self._requirements = requirements
        self._documents = documents
        self._crud = crud

    @router.get(
        '/requirements/{requirement_id}/measures', 
        response_model=list[MeasureOutput], **kwargs)
    def _list_measures(self, requirement_id: int) -> Iterator[MeasureOutput]:
        # get requirement output
        requirement_output = self._requirements._get_requirement(requirement_id)
        
        # get jira issues linked to measures
        measures = self.list_measures(requirement_id)
        jira_issue_ids = [m.jira_issue_id for m in measures if m.jira_issue_id]
        jira_issues = self._jira_issues.get_jira_issues(jira_issue_ids)
        jira_issue_map = {ji.id:ji for ji in jira_issues}

        for measure in measures:
            # get document output
            document_output = self._documents._try_to_get_document(
                measure.document_id)

            # get jira issue
            try:
                jira_issue = jira_issue_map[measure.jira_issue_id]
            except KeyError:
                jira_issue = None

            yield MeasureOutput.from_orm(measure, update=dict(
                requirement=requirement_output, document=document_output,
                jira_issue=jira_issue))

    def list_measures(self, requirement_id: int) -> list[Measure]:
        return self._crud.read_all_from_db(
            Measure, requirement_id=requirement_id)

    @router.post(
        '/requirements/{requirement_id}/measures', status_code=201,
        response_model=MeasureOutput, **kwargs)
    def _create_measure(
            self, requirement_id: int, 
            measure_input: MeasureInput) -> MeasureOutput:
        requirement_output = self._requirements._get_requirement(requirement_id)
        document_output = self._documents._try_to_get_document(measure_input.document_id)

        return MeasureOutput.from_orm(
            self.create_measure(requirement_id, measure_input), update=dict(
                requirement=requirement_output, document=document_output))

    def create_measure(
            self, requirement_id: int, measure: MeasureInput) -> Measure:
        measure = Measure.from_orm(measure)
        measure.requirement = self._requirements.get_requirement(requirement_id)
        self._documents.check_document_id(measure.document_id)
        return self._crud.create_in_db(measure)

    @router.get(
        '/measures/{measure_id}', response_model=MeasureOutput, **kwargs)
    def _get_measure(self, measure_id: int) -> MeasureOutput:
        measure = self.get_measure(measure_id)
        requirement_output = self._requirements._get_requirement(measure.requirement_id)
        document_output = self._documents._try_to_get_document(measure.document_id)
        jira_issue = self._jira_issues.try_to_get_jira_issue(measure.jira_issue_id)
        
        return MeasureOutput.from_orm(measure, update=dict(
            requirement=requirement_output, document=document_output,
            jira_issue=jira_issue))
        
    def get_measure(self, measure_id: int):
        return self._crud.read_from_db(Measure, measure_id)

    @router.put(
        '/measures/{measure_id}', response_model=MeasureOutput, **kwargs)
    def _update_measure(
            self, measure_id: int, measure_input: MeasureInput) -> MeasureOutput:
        measure = self.update_measure(measure_id, measure_input)
        requirement_output = self._requirements._get_requirement(measure.requirement_id)
        document_output = self._documents._try_to_get_document(measure.document_id)
        jira_issue = self._jira_issues.try_to_get_jira_issue(measure.jira_issue_id)
        
        return MeasureOutput.from_orm(measure, update=dict(
            requirement=requirement_output, document=document_output,
            jira_issue=jira_issue))

    def update_measure(
            self, measure_id: int, measure_update: MeasureInput) -> Measure:
        measure_current = self._crud.read_from_db(Measure, measure_id)
        measure_update = Measure.from_orm(measure_update, update=dict(
            requirement_id=measure_current.requirement_id,
            jira_issue_id=measure_current.jira_issue_id))
        self._documents.check_document_id(measure_update.document_id)
        return self._crud.update_in_db(measure_id, measure_update)

    @router.delete(
        '/measures/{measure_id}', status_code=204, response_class=Response,
        **kwargs)
    def delete_measure(self, measure_id: int) -> None:
        return self._crud.delete_from_db(Measure, measure_id)

    @router.post(
        '/measures/{measure_id}/jira-issue', status_code=201, 
        response_model=JiraIssue, **kwargs)
    def create_and_link_jira_issue(
            self, measure_id: int, 
            jira_issue_input: JiraIssueInput) -> JiraIssue:
        measure = self.get_measure(measure_id)

        # check if jira issue is already linked
        if measure.jira_issue_id is not None:
            detail = 'Measure %d is already linked to Jira issue %s' % (
                measure_id, measure.jira_issue_id)
            raise HTTPException(400, detail)

        # check if a Jira project is assigned to corresponding project
        project = measure.requirement.project
        if project.jira_project_id is None:
            detail = f'No Jira project is assigned to project {project.id}'
            raise HTTPException(400, detail)
        
        # create and link Jira issue
        jira_issue = self._jira_issues.create_jira_issue(
            project.jira_project_id, jira_issue_input)
        measure.jira_issue_id = jira_issue.id
        self._crud.update_in_db(measure_id, measure)
        return jira_issue

    @router.delete(
        '/measures/{measure_id}/jira-issue', status_code=204,
        response_class=Response, **kwargs)
    def unlink_jira_issue(self, measure_id: int) -> None:
        measure = self.get_measure(measure_id)
        if measure.jira_issue_id is None:
            detail = 'Measure %d is not linked to a Jira issue' % measure_id
            raise HTTPException(404, detail)

        # unlink Jira issue
        measure.jira_issue_id = None
        self._crud.update_in_db(measure_id, measure)

    def fill_excel_worksheet_with_measures(self, worksheet: Worksheet, project_id: int):
        # query data
        query = select(Requirement, Measure).where(Requirement.project_id == project_id)
        results = self._crud.session.execute(query)

        # fill worksheet
        worksheet.append([
            'Requirement Reference', 'Requirement Summary', 'Summary', 
            'Description', 'Completed'])
        for requirement, measure in results:
            worksheet.append([
                requirement.reference, requirement.summary, measure.summary,
                measure.description, measure.completed])

        # create table
        table = Table(
            displayName=worksheet.title, ref=worksheet.calculate_dimension())
        worksheet.add_table(table)
        