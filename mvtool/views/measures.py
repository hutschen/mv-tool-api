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
from jira import JIRA
from sqlmodel import Session
from fastapi import APIRouter, Depends, Response
from fastapi_utils.cbv import cbv
from mvtool.views.documents import DocumentsView

from mvtool.views.jira_ import JiraIssuesView
from ..auth import get_jira
from ..database import CRUDOperations, get_session
from .requirements import RequirementsView
from ..models import MeasureInput, Measure, MeasureOutput

router = APIRouter()


@cbv(router)
class MeasuresView(CRUDOperations[Measure]):
    kwargs = dict(tags=['measure'])

    def __init__(
            self, session: Session = Depends(get_session),
            jira: JIRA = Depends(get_jira)):
        super().__init__(session, Measure)
        self.jira_issues = JiraIssuesView(jira)
        self.requirements = RequirementsView(session, jira)
        self.documents = DocumentsView(session, jira)

    @router.get(
        '/requirements/{requirement_id}/measures', 
        response_model=list[MeasureOutput], **kwargs)
    def _list_measures(self, requirement_id: int) -> Iterator[MeasureOutput]:
        measures = self.list_measures(requirement_id)
        jira_issue_ids = [m.jira_issue_id for m in measures if m.jira_issue_id]
        jira_issues = self.jira_issues.get_jira_issues(*jira_issue_ids)
        jira_issue_map = {ji.id:ji for ji in jira_issues}
        for measure in measures:
            measure = MeasureOutput.from_orm(measure)
            try:
                measure.jira_issue = jira_issue_map[measure.jira_issue_id]
            except KeyError:
                pass
            yield measure

    def list_measures(self, requirement_id: int) -> list[Measure]:
        return self.read_all_from_db(requirement_id=requirement_id)

    @router.post(
        '/requirements/{requirement_id}/measures', status_code=201,
        response_model=MeasureOutput, **kwargs)
    def _create_measure(
            self, requirement_id: int, measure: MeasureInput) -> MeasureOutput:
        measure = MeasureOutput.from_orm(
            self.create_measure(requirement_id, measure))
        measure.jira_issue = self.jira_issues.try_to_get_jira_issue(
            measure.jira_issue_id)
        return measure

    def create_measure(
            self, requirement_id: int, measure: MeasureInput) -> Measure:
        measure = Measure.from_orm(measure)
        measure.requirement = self.requirements.get_requirement(requirement_id)
        self.jira_issues.check_jira_issue_id(measure.jira_issue_id)
        self.documents.check_document_id(measure.document_id)
        return self.create_in_db(measure)

    @router.get(
        '/measures/{measure_id}', response_model=MeasureOutput, **kwargs)
    def _get_measure(self, measure_id: int) -> MeasureOutput:
        measure = MeasureOutput.from_orm(self.get_measure(measure_id))
        measure.jira_issue = self.jira_issues.try_to_get_jira_issue(
            measure.jira_issue_id)
        return measure

    def get_measure(self, measure_id: int):
        return self.read_from_db(measure_id)

    @router.put(
        '/measures/{measure_id}', response_model=MeasureOutput, **kwargs)
    def _update_measure(
            self, measure_id: int, measure: MeasureInput) -> MeasureOutput:
        measure = MeasureOutput.from_orm(
            self.update_measure(measure_id, measure))
        measure.jira_issue = self.jira_issues.try_to_get_jira_issue(
            measure.jira_issue_id)
        return measure

    def update_measure(
            self, measure_id: int, measure_update: MeasureInput) -> Measure:
        measure_current = self.read_from_db(measure_id)
        measure_update = Measure.from_orm(measure_update, update=dict(
            requirement_id=measure_current.requirement_id))
        self.documents.check_document_id(measure_update.document_id)
        if measure_update.jira_issue_id != measure_current.jira_issue_id:
            self.jira_issues.check_jira_issue_id(measure_update.jira_issue_id)
        return self.update_in_db(measure_id, measure_update)

    @router.delete(
        '/measures/{measure_id}', status_code=204, response_class=Response,
        **kwargs)
    def delete_measure(self, measure_id: int) -> None:
        return self.delete_in_db(measure_id)