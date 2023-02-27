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
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi_utils.cbv import cbv
from pydantic import constr
from sqlmodel import Column, func, select, or_
from sqlmodel.sql.expression import Select
from mvtool.utils import combine_flags

from mvtool.views.documents import DocumentsView
from mvtool.views.jira_ import JiraIssuesView
from ..utils.pagination import Page, page_params
from ..utils.filtering import (
    filter_for_existence,
    filter_by_pattern,
    filter_by_values,
    search_columns,
)
from ..database import CRUDOperations
from .requirements import RequirementsView
from ..errors import ClientError, NotFoundError
from ..models import (
    Catalog,
    CatalogModule,
    CatalogRequirement,
    Document,
    JiraIssue,
    JiraIssueInput,
    MeasureInput,
    Measure,
    MeasureOutput,
    MeasureRepresentation,
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

    @staticmethod
    def _modify_measures_query(
        query: Select,
        where_clauses: Any = None,
        order_by_clauses: Any = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Select:
        """Modify a query to include all required joins, clauses and offset and limit."""
        query = (
            query.join(Requirement)
            .outerjoin(Document)
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
        return query

    def list_measures(
        self,
        where_clauses: Any = None,
        order_by_clauses: Any = None,
        offset: int | None = None,
        limit: int | None = None,
        query_jira: bool = True,
    ) -> list[Measure]:
        # construct measures query
        query = self._modify_measures_query(
            select(Measure),
            where_clauses,
            order_by_clauses or [Measure.id],
            offset,
            limit,
        )

        # execute measures query
        measures = self._session.exec(query).all()

        # set jira project and issue on measures
        if query_jira:
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
        query = self._modify_measures_query(
            select([func.count()]).select_from(Measure), where_clauses
        )
        return self._session.execute(query).scalar()

    def list_measure_values(
        self,
        column: Column,
        where_clauses: Any = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        query = self._modify_measures_query(
            select([func.distinct(column)]).select_from(Measure),
            [filter_for_existence(column), *where_clauses],
            offset=offset,
            limit=limit,
        )
        return self._session.exec(query).all()

    def count_measure_values(self, column: Column, where_clauses: Any = None) -> int:
        query = self._modify_measures_query(
            select([func.count(func.distinct(column))]).select_from(Measure),
            [filter_for_existence(column), *where_clauses],
        )
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
    # filter by pattern
    reference: str | None = None,
    summary: str | None = None,
    description: str | None = None,
    compliance_comment: str | None = None,
    completion_comment: str | None = None,
    verification_comment: str | None = None,
    #
    # filter by values
    references: list[str] | None = Query(default=None),
    compliance_statuses: list[str] | None = Query(default=None),
    completion_statuses: list[str] | None = Query(default=None),
    verified: bool | None = None,
    verification_methods: list[str] | None = Query(default=None),
    #
    # filter by ids
    ids: list[int] | None = Query(default=None),
    document_ids: list[int] | None = Query(default=None),
    jira_issue_ids: list[str] | None = Query(default=None),
    project_ids: list[int] | None = Query(default=None),
    requirement_ids: list[int] | None = Query(default=None),
    catalog_requirement_ids: list[int] | None = Query(default=None),
    catalog_module_ids: list[int] | None = Query(default=None),
    catalog_ids: list[int] | None = Query(default=None),
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
    has_catalog: bool | None = None,
    has_catalog_module: bool | None = None,
    has_catalog_requirement: bool | None = None,
    #
    # filter by search string
    search: str | None = None,
) -> list[Any]:
    where_clauses = []

    # filter by pattern
    for column, value in [
        (Measure.reference, reference),
        (Measure.summary, summary),
        (Measure.description, description),
        (Measure.compliance_comment, compliance_comment),
        (Measure.completion_comment, completion_comment),
        (Measure.verification_comment, verification_comment),
    ]:
        if value is not None:
            where_clauses.append(filter_by_pattern(column, value))

    # filter by values or by ids
    for column, values in [
        (Measure.reference, references),
        (Measure.compliance_status, compliance_statuses),
        (Measure.completion_status, completion_statuses),
        (Measure.verification_method, verification_methods),
        (Measure.id, ids),
        (Measure.document_id, document_ids),
        (Measure.jira_issue_id, jira_issue_ids),
        (Requirement.project_id, project_ids),
        (Measure.requirement_id, requirement_ids),
        (Requirement.catalog_requirement_id, catalog_requirement_ids),
        (CatalogRequirement.catalog_module_id, catalog_module_ids),
        (CatalogModule.catalog_id, catalog_ids),
    ]:
        if values:
            where_clauses.append(filter_by_values(column, values))

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
        (
            Requirement.catalog_requirement_id,
            combine_flags(has_catalog_requirement, has_catalog_module, has_catalog),
        ),
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
                    Document.reference,
                    Document.title,
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


def get_measure_sort(
    sort_by: str | None = None, sort_order: constr(regex=r"^(asc|desc)$") | None = None
) -> list[Any]:
    if not (sort_by and sort_order):
        return []

    try:
        columns: list[Column] = {
            "reference": [Measure.reference],
            "summary": [Measure.summary],
            "description": [Measure.description],
            "compliance_status": [Measure.compliance_status],
            "compliance_comment": [Measure.compliance_comment],
            "completion_status": [Measure.completion_status],
            "completion_comment": [Measure.completion_comment],
            "verified": [Measure.verified],
            "verification_method": [Measure.verification_method],
            "verification_comment": [Measure.verification_comment],
            "document": [Document.reference, Document.title],
            "jira_issue": [Measure.jira_issue_id],
            "requirement": [Requirement.reference, Requirement.summary],
            "catalog_requirement": [
                CatalogRequirement.reference,
                CatalogRequirement.summary,
            ],
            "catalog_module": [CatalogModule.reference, CatalogModule.title],
            "catalog": [Catalog.reference, Catalog.title],
        }[sort_by]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by parameter: {sort_by}",
        )

    columns.append(Measure.id)
    if sort_order == "asc":
        return [column.asc() for column in columns]
    else:
        return [column.desc() for column in columns]


@router.get(
    "/measures",
    response_model=Page[MeasureOutput] | list[MeasureOutput],
    **MeasuresView.kwargs,
)
def get_measures(
    where_clauses=Depends(get_measure_filters),
    order_by_clauses=Depends(get_measure_sort),
    page_params=Depends(page_params),
    measures_view: MeasuresView = Depends(),
):
    measures = measures_view.list_measures(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        measures_count = measures_view.count_measures(where_clauses)
        return Page[MeasureOutput](items=measures, total_count=measures_count)
    else:
        return measures


@router.get(
    "/measure/representations",
    response_model=Page[MeasureRepresentation] | list[MeasureRepresentation],
    **MeasuresView.kwargs,
)
def get_measure_representations(
    where_clauses: list[Any] = Depends(get_measure_filters),
    local_search: str | None = None,
    order_by_clauses=Depends(get_measure_sort),
    page_params=Depends(page_params),
    measures_view: MeasuresView = Depends(),
):
    if local_search:
        where_clauses.append(
            search_columns(local_search, Measure.reference, Measure.summary)
        )

    measures = measures_view.list_measures(
        where_clauses, order_by_clauses, **page_params, query_jira=False
    )
    if page_params:
        measures_count = measures_view.count_measures(where_clauses)
        return Page[MeasureRepresentation](items=measures, total_count=measures_count)
    else:
        return measures


@router.get(
    "/measure/field-names",
    response_model=list[str],
    **MeasuresView.kwargs,
)
def get_measure_field_names(
    where_clauses=Depends(get_measure_filters),
    measures_view: MeasuresView = Depends(),
) -> set[str]:
    field_names = {"id", "summary", "verified", "requirement", "project"}
    for field, names in [
        (Measure.reference, ["reference"]),
        (Measure.description, ["description"]),
        (Measure.compliance_status, ["compliance_status"]),
        (Measure.compliance_comment, ["compliance_comment"]),
        (Measure.completion_status, ["completion_status"]),
        (Measure.completion_comment, ["completion_comment"]),
        (Measure.verification_method, ["verification_method"]),
        (Measure.verification_comment, ["verification_comment"]),
        (Measure.document_id, ["document"]),
        (Measure.jira_issue_id, ["jira_issue"]),
        (
            Requirement.catalog_requirement_id,
            ["catalog_requirement", "catalog_module", "catalog"],
        ),
        (Requirement.milestone, ["milestone"]),
        (Requirement.target_object, ["target_object"]),
    ]:
        if measures_view.count_measures(
            [filter_for_existence(field, True), *where_clauses]
        ):
            field_names.update(names)
    return field_names


@router.get(
    "/measure/references",
    response_model=Page[str] | list[str],
    **MeasuresView.kwargs,
)
def get_measure_references(
    where_clauses=Depends(get_measure_filters),
    local_search: str | None = None,
    page_params=Depends(page_params),
    measures_view: MeasuresView = Depends(),
):
    if local_search:
        where_clauses.append(search_columns(local_search, Measure.reference))

    references = measures_view.list_measure_values(
        Measure.reference, where_clauses, **page_params
    )
    if page_params:
        references_count = measures_view.count_measure_values(
            Measure.reference, where_clauses
        )
        return Page[str](items=references, total_count=references_count)
    else:
        return references
