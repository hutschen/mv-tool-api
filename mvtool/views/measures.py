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


from typing import Any, Iterable, Iterator

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import constr
from sqlmodel import Column, Session, func, or_, select
from sqlmodel.sql.expression import Select

from ..database import delete_from_db, get_session, read_from_db
from ..models.catalog_modules import CatalogModule
from ..models.catalog_requirements import CatalogRequirement
from ..models.catalogs import Catalog
from ..models.documents import Document
from ..models.jira_ import JiraIssue, JiraIssueInput
from ..models.measures import (
    Measure,
    MeasureImport,
    MeasureInput,
    MeasureOutput,
    MeasureRepresentation,
)
from ..models.projects import Project
from ..models.requirements import Requirement
from ..utils import combine_flags
from ..utils.errors import NotFoundError, ValueHttpError
from ..utils.etag_map import get_from_etag_map
from ..utils.fallback import fallback
from ..utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
    search_columns,
)
from ..utils.iteration import CachedIterable
from ..utils.models import field_is_set
from ..utils.pagination import Page, page_params
from ..views.documents import DocumentsView
from ..views.jira_ import JiraIssuesView, JiraProjectsView
from .requirements import RequirementsView

router = APIRouter()


class MeasuresView:
    kwargs = dict(tags=["measure"])

    def __init__(
        self,
        jira_issues: JiraIssuesView = Depends(JiraIssuesView),
        requirements: RequirementsView = Depends(RequirementsView),
        documents: DocumentsView = Depends(DocumentsView),
        session: Session = Depends(get_session),
    ):
        self._jira_issues = jira_issues
        self._requirements = requirements
        self._documents = documents
        self.session = session

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
        measures = self.session.exec(query).all()

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
        return self.session.execute(query).scalar()

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
        return self.session.exec(query).all()

    def count_measure_values(self, column: Column, where_clauses: Any = None) -> int:
        query = self._modify_measures_query(
            select([func.count(func.distinct(column))]).select_from(Measure),
            [filter_for_existence(column), *where_clauses],
        )
        return self.session.execute(query).scalar()

    def create_measure(
        self,
        requirement: Requirement,
        creation: MeasureInput | MeasureImport,
        skip_flush: bool = False,
    ) -> Measure:
        measure = Measure(
            **creation.dict(exclude={"id", "requirement", "jira_issue", "document"})
        )
        measure.requirement = requirement

        # check ids of dependencies
        try_to_get_jira_issue = True
        if isinstance(creation, MeasureInput):
            measure.document = self._documents.check_document_id(creation.document_id)
            self._jira_issues.check_jira_issue_id(creation.jira_issue_id)
            try_to_get_jira_issue = False

        self.session.add(measure)
        if not skip_flush:
            self.session.flush()

        self._set_jira_issue(measure, try_to_get=try_to_get_jira_issue)
        return measure

    def get_measure(self, measure_id: int) -> Measure:
        measure = read_from_db(self.session, Measure, measure_id)
        self._set_jira_issue(measure)
        self._set_jira_project(measure)
        return measure

    def update_measure(
        self,
        measure: Measure,
        update: MeasureInput | MeasureImport,
        patch: bool = False,
        skip_flush: bool = False,
    ) -> None:
        # check ids of dependencies
        try_to_get_jira_issue = True
        if isinstance(update, MeasureInput):
            measure.document = self._documents.check_document_id(update.document_id)
            if update.jira_issue_id != measure.jira_issue_id:
                self._jira_issues.check_jira_issue_id(update.jira_issue_id)
                try_to_get_jira_issue = False

        # update measure
        for key, value in update.dict(
            exclude_unset=patch, exclude={"id", "requirement", "jira_issue", "document"}
        ).items():
            setattr(measure, key, value)

        # flush changes
        if not skip_flush:
            self.session.flush()

        self._set_jira_issue(measure, try_to_get=try_to_get_jira_issue)

    def delete_measure(self, measure: Measure, skip_flush: bool = False) -> None:
        return delete_from_db(self.session, measure, skip_flush)

    def bulk_create_update_measures(
        self,
        measure_imports: Iterable[MeasureImport],
        fallback_requirement: Requirement | None = None,
        fallback_project: Project | None = None,
        fallback_catalog_module: CatalogModule | None = None,
        patch: bool = False,
        skip_flush: bool = False,
    ) -> Iterator[Measure]:
        measure_imports = CachedIterable(measure_imports)

        # Convert requirement imports to requirements
        requirements_map = self._requirements.convert_requirement_imports(
            (m.requirement for m in measure_imports if m.requirement is not None),
            fallback_project,
            fallback_catalog_module,
            patch=patch,
        )

        # Convert document imports to documents
        documents_map = self._documents.convert_document_imports(
            (m.document for m in measure_imports if m.document is not None),
            fallback_project,
            patch=patch,
        )

        # Cache jira issues
        jira_issues_map = {
            ji.key: ji
            for ji in self._jira_issues.get_jira_issues(
                {m.jira_issue.key for m in measure_imports if m.jira_issue is not None}
            )
        }

        # Get measures to be updated from the database
        ids = {m.id for m in measure_imports if m.id is not None}
        measures_to_update = {
            m.id: m for m in (self.list_measures([Measure.id.in_(ids)]) if ids else [])
        }

        # Create or update measures
        for measure_import in measure_imports:
            requirement = get_from_etag_map(
                requirements_map, measure_import.requirement
            )

            if measure_import.id is None:
                # Create measure
                measure = self.create_measure(
                    fallback(
                        requirement,
                        fallback_requirement,
                        "No fallback requirement provided.",
                    ),
                    skip_flush=True,
                )
            else:
                # Update measure
                measure = measures_to_update.get(measure_import.id)
                if measure is None:
                    raise NotFoundError(f"No measure with id={measure_import.id}.")
                self.update_measure(
                    measure,
                    measure_import,
                    patch=patch,
                    skip_flush=True,
                )

            # Set document
            if field_is_set(measure_import, "document") or not patch:
                measure.document = get_from_etag_map(
                    documents_map, measure_import.document
                )

            # Set jira issue
            if field_is_set(measure_import, "jira_issue") or not patch:
                jira_issue = None
                if measure_import.jira_issue is not None:
                    jira_issue = jira_issues_map.get(measure_import.jira_issue.key)
                    if jira_issue is None:
                        raise NotFoundError(
                            f"No Jira issue with key={measure_import.jira_issue.key}."
                        )
                measure.jira_issue_id = jira_issue.id if jira_issue else None

            yield measure

        if not skip_flush:
            self.session.flush()

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
    target_object: str | None = None,
    milestone: str | None = None,
    #
    # filter by values
    references: list[str] | None = Query(default=None),
    compliance_statuses: list[str] | None = Query(default=None),
    completion_statuses: list[str] | None = Query(default=None),
    verification_statuses: list[str] | None = Query(default=None),
    verification_methods: list[str] | None = Query(default=None),
    target_objects: list[str] | None = Query(default=None),
    milestones: list[str] | None = Query(default=None),
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
    has_verification_status: bool | None = None,
    has_verification_method: bool | None = None,
    has_verification_comment: bool | None = None,
    has_document: bool | None = None,
    has_jira_issue: bool | None = None,
    has_catalog: bool | None = None,
    has_catalog_module: bool | None = None,
    has_catalog_requirement: bool | None = None,
    has_target_object: bool | None = None,
    has_milestone: bool | None = None,
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
        (Requirement.target_object, target_object),
        (Requirement.milestone, milestone),
    ]:
        if value is not None:
            where_clauses.append(filter_by_pattern(column, value))

    # filter by values or by ids
    for column, values in [
        (Measure.reference, references),
        (Measure.compliance_status, compliance_statuses),
        (Measure.completion_status, completion_statuses),
        (Measure.verification_status, verification_statuses),
        (Measure.verification_method, verification_methods),
        (Measure.id, ids),
        (Measure.document_id, document_ids),
        (Measure.jira_issue_id, jira_issue_ids),
        (Requirement.project_id, project_ids),
        (Measure.requirement_id, requirement_ids),
        (Requirement.catalog_requirement_id, catalog_requirement_ids),
        (CatalogRequirement.catalog_module_id, catalog_module_ids),
        (CatalogModule.catalog_id, catalog_ids),
        (Requirement.target_object, target_objects),
        (Requirement.milestone, milestones),
    ]:
        if values:
            where_clauses.append(filter_by_values(column, values))

    # filter for existence
    for column, value in [
        (Measure.reference, has_reference),
        (Measure.description, has_description),
        (Measure.compliance_status, has_compliance_status),
        (Measure.compliance_comment, has_compliance_comment),
        (Measure.completion_status, has_completion_status),
        (Measure.completion_comment, has_completion_comment),
        (Measure.verification_status, has_verification_status),
        (Measure.verification_method, has_verification_method),
        (Measure.verification_comment, has_verification_comment),
        (Measure.document_id, has_document),
        (Measure.jira_issue_id, has_jira_issue),
        (
            Requirement.catalog_requirement_id,
            combine_flags(has_catalog_requirement, has_catalog_module, has_catalog),
        ),
        (Requirement.target_object, has_target_object),
        (Requirement.milestone, has_milestone),
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
            "verification_status": [Measure.verification_status],
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
            "target_object": [Requirement.target_object],
            "milestone": [Requirement.milestone],
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


@router.post(
    "/requirements/{requirement_id}/measures",
    status_code=201,
    response_model=MeasureOutput,
    **MeasuresView.kwargs,
)
def create_measure(
    requirement_id: int,
    measure_input: MeasureInput,
    requirements_view: RequirementsView = Depends(),
    measures_view: MeasuresView = Depends(),
) -> Measure:
    requirement = requirements_view.get_requirement(requirement_id)
    return measures_view.create_measure(requirement, measure_input)


@router.get(
    "/measures/{measure_id}", response_model=MeasureOutput, **MeasuresView.kwargs
)
def get_measure(measure_id: int, measures_view: MeasuresView = Depends()) -> Measure:
    return measures_view.get_measure(measure_id)


@router.put(
    "/measures/{measure_id}", response_model=MeasureOutput, **MeasuresView.kwargs
)
def update_measure(
    measure_id: int,
    measure_input: MeasureInput,
    measures_view: MeasuresView = Depends(),
):
    measure = measures_view.get_measure(measure_id)
    measures_view.update_measure(measure, measure_input)
    return measure


@router.delete(
    "/measures/{measure_id}",
    status_code=204,
    response_class=Response,
    **MeasuresView.kwargs,
)
def delete_measure(measure_id: int, measures_view: MeasuresView = Depends()):
    measure = measures_view.get_measure(measure_id)
    measures_view.delete_measure(measure)


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
    field_names = {"project", "requirement", "id", "summary", "completion_status"}
    for field, names in [
        (Measure.reference, ["reference"]),
        (Measure.description, ["description"]),
        (Measure.compliance_status, ["compliance_status"]),
        (Measure.compliance_comment, ["compliance_comment"]),
        (Measure.completion_comment, ["completion_comment"]),
        (Measure.verification_status, ["verification_status"]),
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


@router.post(
    "/measures/{measure_id}/jira-issue",
    status_code=201,
    response_model=JiraIssue,
    **JiraIssuesView.kwargs,
)
def create_and_link_jira_issue_to_measure(
    measure_id: int,
    jira_issue_input: JiraIssueInput,
    measures_view: MeasuresView = Depends(),
    jira_issues_view: JiraIssuesView = Depends(),
    jira_projects_view: JiraProjectsView = Depends(),
) -> JiraIssue:
    measure = measures_view.get_measure(measure_id)

    # check if a Jira project is assigned to corresponding project
    project = measure.requirement.project
    if project.jira_project_id is None:
        raise ValueHttpError(f"No Jira project is assigned to project {project.id}")

    # load jira project to check if user has permission to create Jira issues
    jira_projects_view.check_jira_project_id(project.jira_project_id)

    # create and link Jira issue
    jira_issue = jira_issues_view.create_jira_issue(
        project.jira_project_id, jira_issue_input
    )
    measure.jira_issue_id = jira_issue.id
    measures_view.session.flush()
    return jira_issue
