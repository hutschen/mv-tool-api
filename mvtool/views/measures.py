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


from typing import Any, Iterator
from fastapi import APIRouter, Depends, Response
from fastapi_utils.cbv import cbv
from sqlmodel import select

from mvtool.views.documents import DocumentsView
from mvtool.views.jira_ import JiraIssuesView
from ..database import CRUDOperations
from .requirements import RequirementsView
from ..errors import ClientError, NotFoundError
from ..models import (
    JiraIssue,
    JiraIssueInput,
    JiraProject,
    MeasureInput,
    Measure,
    MeasureOutput,
)

router = APIRouter()


@cbv(router)
class MeasuresView:
    kwargs = dict(tags=["measure"])

    def __init__(
        self,
        jira_issues: JiraIssuesView = Depends(JiraIssuesView),
        requirements: RequirementsView = Depends(RequirementsView),
        documents: DocumentsView = Depends(DocumentsView),
        crud: CRUDOperations[Measure] = Depends(CRUDOperations),
    ):
        self._jira_issues = jira_issues
        self._requirements = requirements
        self._documents = documents
        self._crud = crud
        self._session = self._crud.session

    @router.get(
        "/requirements/{requirement_id}/measures",
        response_model=list[MeasureOutput],
        **kwargs,
    )
    def list_measures(self, requirement_id: int) -> Iterator[Measure]:
        requirement = None
        for measure in self.query_measures(Measure.requirement_id == requirement_id):
            if requirement is None:
                requirement = measure.requirement
                self._set_jira_project(measure)

            self._set_jira_project(measure, requirement.project.jira_project)
            yield measure

    def query_measures(self, *whereclauses: Any) -> Iterator[Measure]:
        measures = self._session.exec(
            select(Measure).where(*whereclauses).order_by(Measure.id)
        ).all()

        # query jira issues
        jira_issue_ids = [m.jira_issue_id for m in measures if m.jira_issue_id]
        jira_issues = self._jira_issues.get_jira_issues(jira_issue_ids)
        jira_issue_map = {ji.id: ji for ji in jira_issues}

        # assign jira issue to measure and yield results
        for measure in measures:
            jira_issue = jira_issue_map.get(measure.jira_issue_id, None)
            self._set_jira_issue(measure, jira_issue)
            yield measure

    @router.post(
        "/requirements/{requirement_id}/measures",
        status_code=201,
        response_model=MeasureOutput,
        **kwargs,
    )
    def create_measure(
        self, requirement_id: int, measure_input: MeasureInput
    ) -> Measure:
        requirement = self._requirements.get_requirement(requirement_id)

        # check document id and cache loaded document
        if measure_input.document_id is None:
            document = None
        else:
            document = self._documents.get_document(measure_input.document_id)

        # check jira issue id and cache loaded jira issue
        if measure_input.jira_issue_id is None:
            jira_issue = None
        else:
            jira_issue = self._jira_issues.get_jira_issue(measure_input.jira_issue_id)

        measure = Measure.from_orm(measure_input)
        measure.requirement = requirement
        measure.document = document
        self._set_jira_project_and_issue(measure, jira_issue=jira_issue)
        return self._crud.create_in_db(measure)

    @router.get("/measures/{measure_id}", response_model=MeasureOutput, **kwargs)
    def get_measure(self, measure_id: int) -> Measure:
        measure = self._crud.read_from_db(Measure, measure_id)
        self._set_jira_project_and_issue(measure)
        return measure

    @router.put("/measures/{measure_id}", response_model=MeasureOutput, **kwargs)
    def update_measure(self, measure_id: int, measure_input: MeasureInput) -> Measure:
        measure = self._session.get(Measure, measure_id)
        if measure is None:
            cls_name = Measure.__name__
            raise NotFoundError(f"No {cls_name} with id={measure_id}.")

        # check jira issue id and cache loaded jira issue
        if (
            measure_input.jira_issue_id is not None
            and measure_input.jira_issue_id != measure.jira_issue_id
        ):
            jira_issue = self._jira_issues.get_jira_issue(measure_input.jira_issue_id)
        else:
            jira_issue = None

        for key, value in measure_input.dict().items():
            setattr(measure, key, value)

        # check document id and set loaded document
        if measure_input.document_id is not None:
            measure.document = self._documents.get_document(measure_input.document_id)

        self._session.flush()
        self._set_jira_project_and_issue(measure, jira_issue=jira_issue)
        return measure

    @router.delete(
        "/measures/{measure_id}", status_code=204, response_class=Response, **kwargs
    )
    def delete_measure(self, measure_id: int) -> None:
        return self._crud.delete_from_db(Measure, measure_id)

    @router.post(
        "/measures/{measure_id}/jira-issue",
        status_code=201,
        response_model=JiraIssue,
        **JiraIssuesView.kwargs,
    )
    def create_and_link_jira_issue(
        self, measure_id: int, jira_issue_input: JiraIssueInput
    ) -> JiraIssue:
        measure = self.get_measure(measure_id)

        # check if a jira issue is already linked
        if measure.jira_issue_id is not None:
            detail = "Measure %d is already linked to Jira issue %s" % (
                measure_id,
                measure.jira_issue_id,
            )
            raise ClientError(detail)

        # check if a Jira project is assigned to corresponding project
        project = measure.requirement.project
        if project.jira_project_id is None:
            detail = f"No Jira project is assigned to project {project.id}"
            raise ClientError(detail)

        # create and link Jira issue
        jira_issue = self._jira_issues.create_jira_issue(
            project.jira_project_id, jira_issue_input
        )
        measure.jira_issue_id = jira_issue.id
        self._crud.update_in_db(measure_id, measure)
        return jira_issue

    def _set_jira_project(
        self, measure: Measure, jira_project: JiraProject | None = None
    ) -> None:
        self._requirements._set_jira_project(measure.requirement, jira_project)
        if measure.document is not None:
            self._documents._set_jira_project(measure.document, jira_project)

    def _set_jira_issue(
        self, measure: Measure, jira_issue: JiraIssue | None = None
    ) -> None:
        measure._jira_issue = jira_issue
        measure._get_jira_issue = self._jira_issues.try_to_get_jira_issue

    def _set_jira_project_and_issue(
        self,
        measure: Measure,
        jira_project: JiraProject | None = None,
        jira_issue: JiraIssue | None = None,
    ) -> None:
        self._set_jira_project(measure, jira_project)
        self._set_jira_issue(measure, jira_issue)
