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


from typing import Any
from fastapi import APIRouter, Depends, Query, Response
from fastapi_utils.cbv import cbv
from sqlmodel import func, select, or_

from mvtool.views.documents import DocumentsView
from mvtool.views.jira_ import JiraIssuesView
from ..utils.pagination import Page, page_params
from ..utils.filtering import (
    filter_for_existence,
    filter_by_pattern,
    filter_column_by_values,
)
from ..database import CRUDOperations
from .requirements import RequirementsView
from ..errors import ClientError, NotFoundError
from ..models import (
    Catalog,
    CatalogModule,
    CatalogRequirement,
    JiraIssue,
    JiraIssueInput,
    MeasureInput,
    Measure,
    MeasureOutput,
    Requirement,
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

    def list_measures(
        self,
        where_clauses: Any = None,
        order_by_clauses: Any = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Measure]:
        # construct measures query
        query = (
            select(Measure)
            .join(Requirement)
            .outerjoin(CatalogRequirement)
            .outerjoin(CatalogModule)
            .outerjoin(Catalog)
        )
        if where_clauses:
            query = query.where(*where_clauses)
        if order_by_clauses:
            query = query.order_by(*order_by_clauses)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        # execute measures query
        measures = self._session.exec(query).all()

        # set jira project and issue on measures
        jira_issue_ids = set()
        for measure in measures:
            if measure.jira_issue_id is not None:
                jira_issue_ids.add(measure.jira_issue_id)
            self._set_jira_issue(measure, try_to_get=False)
            self._set_jira_project(measure)

        # cache jira issues and return measures
        list(self._jira_issues.get_jira_issues(jira_issue_ids))
        return measures

    def count_measures(self, where_clauses: Any = None) -> int:
        # construct measures query
        query = (
            select([func.count()])
            .select_from(Measure)
            .join(Requirement)
            .outerjoin(CatalogRequirement)
            .outerjoin(CatalogModule)
            .outerjoin(Catalog)
        )
        if where_clauses:
            query = query.where(*where_clauses)

        # execute measures query
        return self._session.execute(query).scalar()

    @router.post(
        "/requirements/{requirement_id}/measures",
        status_code=201,
        response_model=MeasureOutput,
        **kwargs,
    )
    def create_measure(
        self, requirement_id: int, measure_input: MeasureInput
    ) -> Measure:

        # check ids of dependencies
        requirement = self._requirements.get_requirement(requirement_id)
        document = self._documents.check_document_id(measure_input.document_id)
        self._jira_issues.check_jira_issue_id(measure_input.jira_issue_id)

        # create measure
        measure = Measure.from_orm(measure_input)
        measure.requirement = requirement
        measure.document = document

        # set jira lookup functions
        self._set_jira_issue(measure, try_to_get=False)
        self._set_jira_project(measure)

        return self._crud.create_in_db(measure)

    @router.get("/measures/{measure_id}", response_model=MeasureOutput, **kwargs)
    def get_measure(self, measure_id: int) -> Measure:
        measure = self._crud.read_from_db(Measure, measure_id)
        self._set_jira_issue(measure)
        self._set_jira_project(measure)
        return measure

    @router.put("/measures/{measure_id}", response_model=MeasureOutput, **kwargs)
    def update_measure(self, measure_id: int, measure_input: MeasureInput) -> Measure:
        measure = self._session.get(Measure, measure_id)
        if measure is None:
            cls_name = Measure.__name__
            raise NotFoundError(f"No {cls_name} with id={measure_id}.")

        # check jira issue id and cache loaded jira issue
        if measure_input.jira_issue_id != measure.jira_issue_id:
            self._jira_issues.check_jira_issue_id(measure_input.jira_issue_id)

        for key, value in measure_input.dict().items():
            setattr(measure, key, value)

        # check document id and set loaded document
        measure.document = self._documents.check_document_id(measure_input.document_id)

        self._session.flush()
        self._set_jira_issue(measure)
        self._set_jira_project(measure)
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

    def _set_jira_project(self, measure: Measure, try_to_get: bool = True) -> None:
        self._requirements._set_jira_project(measure.requirement, try_to_get)
        if measure.document is not None:
            self._documents._set_jira_project(measure.document, try_to_get)

    def _set_jira_issue(self, measure: Measure, try_to_get: bool = True) -> None:
        measure._get_jira_issue = (
            lambda jira_issue_id: self._jira_issues.lookup_jira_issue(
                jira_issue_id, try_to_get
            )
        )


def get_measure_filters(
    # filter by values
    reference: list[str] | None = Query(default=None),
    summary: str | None = None,
    description: str | None = None,
    compliance_status: list[str] | None = Query(default=None),
    compliance_comment: str | None = None,
    completion_status: list[str] | None = Query(default=None),
    completion_comment: str | None = None,
    verified: bool | None = None,
    verification_method: list[str] | None = Query(default=None),
    verification_comment: str | None = None,
    #
    # filter by ids
    document_id: list[int] | None = Query(default=None),
    jira_issue_id: list[str] | None = Query(default=None),
    project_id: list[int] | None = Query(default=None),
    requirement_id: list[int] | None = Query(default=None),
    catalog_requirement_id: list[int] | None = Query(default=None),
    catalog_module_id: list[int] | None = Query(default=None),
    catalog_id: list[int] | None = Query(default=None),
    #
    # filter for existence
    has_reference: bool | None = None,
    has_description: bool | None = None,
    has_compliance_status: bool | None = None,
    has_compliance_comment: bool | None = None,
    has_completion_status: bool | None = None,
    has_completion_comment: bool | None = None,
    has_verification_method: bool | None = None,
    has_verification_comment: bool | None = None,
    has_document: bool | None = None,
    has_jira_issue: bool | None = None,
    has_catalog_requirement: bool | None = None,
    has_catalog_module: bool | None = None,
    has_catalog: bool | None = None,
    #
    # filter by search string
    search: str | None = None,
) -> list[Any]:
    where_clauses = []

    # filter by pattern
    for column, value in [
        (Measure.summary, summary),
        (Measure.description, description),
        (Measure.compliance_comment, compliance_comment),
        (Measure.completion_comment, completion_comment),
        (Measure.verification_comment, verification_comment),
    ]:
        if value is not None:
            where_clauses.append(filter_by_pattern(column, value))

    # filter by values
    for column, values in [
        (Measure.reference, reference),
        (Measure.compliance_status, compliance_status),
        (Measure.completion_status, completion_status),
        (Measure.verification_method, verification_method),
        (Measure.document_id, document_id),
        (Measure.jira_issue_id, jira_issue_id),
        (Requirement.project_id, project_id),
        (Measure.requirement_id, requirement_id),
        (Requirement.catalog_requirement_id, catalog_requirement_id),
        (CatalogRequirement.catalog_module_id, catalog_module_id),
        (CatalogModule.catalog_id, catalog_id),
    ]:
        if values:
            where_clauses.append(filter_column_by_values(column, values))

    if verified is not None:
        where_clauses.append(Measure.verified == verified)

    # filter for existence
    for column, value in [
        (Measure.reference, has_reference),
        (Measure.description, has_description),
        (Measure.compliance_status, has_compliance_status),
        (Measure.compliance_comment, has_compliance_comment),
        (Measure.completion_status, has_completion_status),
        (Measure.completion_comment, has_completion_comment),
        (Measure.verification_method, has_verification_method),
        (Measure.verification_comment, has_verification_comment),
        (Measure.document_id, has_document),
        (Measure.jira_issue_id, has_jira_issue),
        (Requirement.catalog_requirement_id, has_catalog_requirement),
        (CatalogRequirement.catalog_module_id, has_catalog_module),
        (CatalogModule.catalog_id, has_catalog),
    ]:
        if value is not None:
            where_clauses.append(filter_for_existence(column, value))

    # filter by search string
    if search:
        where_clauses.append(
            or_(
                filter_by_pattern(column, f"*{search}*")
                for column in (
                    Measure.reference,
                    Measure.summary,
                    Measure.description,
                    Measure.compliance_comment,
                    Measure.completion_comment,
                    Measure.verification_comment,
                    Requirement.reference,
                    Requirement.summary,
                    CatalogRequirement.reference,
                    CatalogRequirement.summary,
                    CatalogModule.reference,
                    CatalogModule.title,
                    Catalog.reference,
                    Catalog.title,
                )
            )
        )

    return where_clauses


@router.get(
    "/measures",
    response_model=Page[MeasureOutput] | list[MeasureOutput],
    **MeasuresView.kwargs,
)
def get_measures(
    where_clauses=Depends(get_measure_filters),
    page_params=Depends(page_params),
    measures_view: MeasuresView = Depends(MeasuresView),
):
    measures = measures_view.list_measures(where_clauses, **page_params)
    if page_params:
        measures_count = measures_view.count_measures(where_clauses)
        return Page[MeasureOutput](items=measures, total_count=measures_count)
    else:
        return measures
