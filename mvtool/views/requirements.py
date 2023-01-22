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
from fastapi import APIRouter, Depends, Query
from fastapi_utils.cbv import cbv
from sqlmodel import Column, func, or_, select
from sqlmodel.sql.expression import Select

from ..utils.pagination import Page, page_params
from ..utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
)
from ..errors import NotFoundError
from ..database import CRUDOperations
from .projects import ProjectsView
from .catalog_requirements import CatalogRequirementsView
from ..models import (
    Catalog,
    CatalogModule,
    CatalogRequirement,
    RequirementInput,
    Requirement,
    RequirementOutput,
    RequirementRepresentation,
)

router = APIRouter()


@cbv(router)
class RequirementsView:
    kwargs = dict(tags=["requirement"])

    def __init__(
        self,
        projects: ProjectsView = Depends(ProjectsView),
        catalog_requirements: CatalogRequirementsView = Depends(
            CatalogRequirementsView
        ),
        crud: CRUDOperations[Requirement] = Depends(CRUDOperations),
    ):
        self._projects = projects
        self._catalog_requirements = catalog_requirements
        self._crud = crud
        self._session = self._crud.session

    @staticmethod
    def _modify_requirements_query(
        query: Select,
        where_clauses: Any = None,
        order_by_clauses: Any = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Select:
        """Modify a query to include all required joins, clauses and offset and limit."""
        query = (
            query.outerjoin(CatalogRequirement)
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

    def list_requirements(
        self,
        where_clauses: Any = None,
        order_by_clauses: Any = None,
        offset: int | None = None,
        limit: int | None = None,
        query_jira: bool = True,
    ) -> list[Requirement]:
        # construct requirements query
        query = self._modify_requirements_query(
            select(Requirement), where_clauses, order_by_clauses, offset, limit
        )

        # execute query, set jira_project and return requirements
        requirements = self._session.exec(query).all()
        if query_jira:
            for requirement in requirements:
                self._set_jira_project(requirement)
        return requirements

    def count_requirements(self, where_clauses: Any = None) -> int:
        query = self._modify_requirements_query(
            select([func.count()]).select_from(Requirement), where_clauses
        )
        return self._session.execute(query).scalar()

    def list_requirement_values(
        self,
        column: Column,
        where_clauses: Any = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        query = self._modify_requirements_query(
            select([func.distinct(column)]).select_from(Requirement),
            [filter_for_existence(column), *where_clauses],
            offset=offset,
            limit=limit,
        )
        return self._session.exec(query).all()

    def count_requirement_values(
        self, column: Column, where_clauses: Any = None
    ) -> int:
        query = self._modify_requirements_query(
            select([func.count(func.distinct(column))]).select_from(Requirement),
            [filter_for_existence(column), *where_clauses],
        )
        return self._session.execute(query).scalar()

    @router.post(
        "/projects/{project_id}/requirements",
        status_code=201,
        response_model=RequirementOutput,
        **kwargs,
    )
    def create_requirement(
        self, project_id: int, requirement_input: RequirementInput
    ) -> Requirement:
        requirement = Requirement.from_orm(requirement_input)
        requirement.project = self._projects.get_project(project_id)
        requirement.catalog_requirement = (
            self._catalog_requirements.check_catalog_requirement_id(
                requirement_input.catalog_requirement_id
            )
        )
        return self._crud.create_in_db(requirement)

    @router.get(
        "/requirements/{requirement_id}", response_model=RequirementOutput, **kwargs
    )
    def get_requirement(self, requirement_id: int) -> Requirement:
        requirement = self._crud.read_from_db(Requirement, requirement_id)
        self._set_jira_project(requirement)
        return requirement

    @router.put(
        "/requirements/{requirement_id}", response_model=RequirementOutput, **kwargs
    )
    def update_requirement(
        self, requirement_id: int, requirement_input: RequirementInput
    ) -> Requirement:
        requirement = self._session.get(Requirement, requirement_id)
        if not requirement:
            cls_name = Requirement.__name__
            raise NotFoundError(f"No {cls_name} with id={requirement_id}.")

        for key, value in requirement_input.dict().items():
            setattr(requirement, key, value)

        # check catalog_requirement_id and set catalog_requirement
        requirement.catalog_requirement = (
            self._catalog_requirements.check_catalog_requirement_id(
                requirement_input.catalog_requirement_id
            )
        )

        self._session.flush()
        self._set_jira_project(requirement)
        return requirement

    @router.delete("/requirements/{requirement_id}", status_code=204, **kwargs)
    def delete_requirement(self, requirement_id: int) -> None:
        return self._crud.delete_from_db(Requirement, requirement_id)

    def _set_jira_project(
        self, requirement: Requirement, try_to_get: bool = True
    ) -> None:
        self._projects._set_jira_project(requirement.project, try_to_get)


@cbv(router)
class ImportCatalogRequirementsView:
    kwargs = RequirementsView.kwargs

    def __init__(
        self,
        projects: ProjectsView = Depends(ProjectsView),
        catalog_requirements: CatalogRequirementsView = Depends(
            CatalogRequirementsView
        ),
        crud: CRUDOperations[Requirement] = Depends(CRUDOperations),
    ):
        self._projects = projects
        self._catalog_requirements = catalog_requirements
        self._crud = crud
        self._session = self._crud.session

    @router.post(
        "/projects/{project_id}/requirements/import",
        status_code=201,
        response_model=list[RequirementOutput],
        **kwargs,
    )
    def import_requirements_from_catalog_modules(
        self, project_id: int, catalog_module_ids: list[int]
    ) -> list[Requirement]:
        project = self._projects.get_project(project_id)
        created_requirements = []

        for (
            catalog_requirement
        ) in self._catalog_requirements.query_catalog_requirements(
            CatalogRequirement.catalog_module_id.in_(catalog_module_ids)
        ):
            requirement = Requirement.from_orm(
                RequirementInput.from_orm(catalog_requirement)
            )
            requirement.catalog_requirement = catalog_requirement
            requirement.project = project
            self._session.add(requirement)
            created_requirements.append(requirement)

        self._session.flush()
        return created_requirements


def get_requirement_filters(
    # filter by pattern
    reference: str | None = None,
    summary: str | None = None,
    description: str | None = None,
    target_object: str | None = None,
    milestone: str | None = None,
    compliance_comment: str | None = None,
    #
    # filter by values
    references: list[str] | None = Query(default=None),
    target_objects: list[str] | None = Query(default=None),
    milestones: list[str] | None = Query(default=None),
    compliance_statuses: list[str] | None = Query(default=None),
    #
    # filter by ids
    project_ids: list[int] | None = Query(default=None),
    catalog_requirement_ids: list[int] | None = Query(default=None),
    catalog_module_ids: list[int] | None = Query(default=None),
    catalog_ids: list[int] | None = Query(default=None),
    #
    # filter for existence
    has_reference: bool | None = None,
    has_description: bool | None = None,
    has_target_object: bool | None = None,
    has_milestone: bool | None = None,
    has_compliance_status: bool | None = None,
    has_compliance_comment: bool | None = None,
    has_catalog_requirement: bool | None = None,
    #
    # filter by search string
    search: str | None = None,
) -> list[Any]:
    where_clauses = []

    # filter by pattern
    for column, value in (
        (Requirement.reference, reference),
        (Requirement.summary, summary),
        (Requirement.description, description),
        (Requirement.target_object, target_object),
        (Requirement.milestone, milestone),
        (Requirement.compliance_comment, compliance_comment),
    ):
        if value:
            where_clauses.append(filter_by_pattern(column, value))

    # filter by values or by ids
    for column, values in (
        (Requirement.reference, references),
        (Requirement.target_object, target_objects),
        (Requirement.milestone, milestones),
        (Requirement.compliance_status, compliance_statuses),
        (Requirement.project_id, project_ids),
        (Requirement.catalog_requirement_id, catalog_requirement_ids),
        (CatalogRequirement.catalog_module_id, catalog_module_ids),
        (CatalogModule.catalog_id, catalog_ids),
    ):
        if values:
            where_clauses.append(filter_by_values(column, values))

    # filter for existence
    for column, value in (
        (Requirement.reference, has_reference),
        (Requirement.description, has_description),
        (Requirement.target_object, has_target_object),
        (Requirement.milestone, has_milestone),
        (Requirement.compliance_status, has_compliance_status),
        (Requirement.compliance_comment, has_compliance_comment),
        (Requirement.catalog_requirement_id, has_catalog_requirement),
    ):
        if value is not None:
            where_clauses.append(filter_for_existence(column, value))

    # filter by search string
    if search:
        where_clauses.append(
            or_(
                filter_by_pattern(column, f"*{search}*")
                for column in (
                    Requirement.reference,
                    Requirement.summary,
                    Requirement.description,
                    Requirement.target_object,
                    Requirement.milestone,
                    Requirement.compliance_comment,
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
    "/requirements",
    response_model=Page[RequirementOutput] | list[RequirementOutput],
    **RequirementsView.kwargs,
)
def get_requirements(
    where_clauses=Depends(get_requirement_filters),
    page_params=Depends(page_params),
    requirements_view: RequirementsView = Depends(RequirementsView),
):
    requirements = requirements_view.list_requirements(where_clauses, **page_params)
    if page_params:
        requirements_count = requirements_view.count_requirements(where_clauses)
        return Page[RequirementOutput](
            items=requirements, total_count=requirements_count
        )
    else:
        return requirements


@router.get(
    "/requirement/representations",
    response_model=Page[RequirementRepresentation] | list[RequirementRepresentation],
    **RequirementsView.kwargs,
)
def get_requirement_representations(
    where_clauses=Depends(get_requirement_filters),
    page_params=Depends(page_params),
    requirements_view: RequirementsView = Depends(RequirementsView),
):
    requirements = requirements_view.list_requirements(
        where_clauses, **page_params, query_jira=False
    )
    if page_params:
        requirements_count = requirements_view.count_requirements(where_clauses)
        return Page[RequirementRepresentation](
            items=requirements, total_count=requirements_count
        )
    else:
        return requirements


@router.get(
    "/requirement/field-names",
    response_model=list[str],
    **RequirementsView.kwargs,
)
def get_requirement_field_names(
    where_clauses=Depends(get_requirement_filters),
    requirements_view: RequirementsView = Depends(RequirementsView),
) -> set[str]:
    field_names = {"id", "summary", "project"}
    for field, names in [
        (Requirement.reference, ["reference"]),
        (Requirement.description, ["description"]),
        (Requirement.target_object, ["target_object"]),
        (Requirement.milestone, ["milestone"]),
        (Requirement.compliance_status, ["compliance_status"]),
        (Requirement.compliance_comment, ["compliance_comment"]),
        (
            Requirement.catalog_requirement_id,
            ["catalog_requirement", "catalog_module", "catalog"],
        ),
    ]:
        if requirements_view.count_requirements(
            [filter_for_existence(field, True), *where_clauses]
        ):
            field_names.update(names)
    return field_names
