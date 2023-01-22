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
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from sqlmodel import func, select
from sqlmodel.sql.expression import Select

from mvtool.utils.pagination import Page, page_params

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
    def _apply_joins_to_requirements_query(query: Select) -> Select:
        return (
            query.outerjoin(CatalogRequirement)
            .outerjoin(CatalogModule)
            .outerjoin(Catalog)
        )

    def list_requirements(self, project_id: int) -> list[Requirement]:
        return self.query_requirements(
            where_clauses=[Requirement.project_id == project_id]
        )

    @router.get(
        "/projects/{project_id}/requirements",
        response_model=Page[RequirementOutput],
        **kwargs,
    )
    def get_requirements_page(
        self, project_id: int, page_params=Depends(page_params)
    ) -> Page[RequirementOutput]:
        where_clauses = [Requirement.project_id == project_id]
        return Page[RequirementOutput](
            items=self.query_requirements(
                where_clauses=where_clauses,
                order_by_clauses=[Requirement.id.asc()],
                **page_params,
            ),
            total_count=self.query_requirement_count(where_clauses=where_clauses),
        )

    def query_requirement_count(self, where_clauses: Any = None) -> int:
        # construct requirements query
        query = select([func.count()]).select_from(Requirement)
        if where_clauses:
            query = query.where(*where_clauses)

        # execute query
        return self._session.execute(query).scalar()

    def query_requirements(
        self,
        where_clauses: Any = None,
        order_by_clauses: Any = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Requirement]:
        # construct requirements query
        query = select(Requirement).select_from(Requirement)
        if where_clauses:
            query = query.where(*where_clauses)
        if order_by_clauses:
            query = query.order_by(*order_by_clauses)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        # execute query, set jira_project and return requirements
        requirements = self._session.execute(query).scalars().all()
        for requirement in requirements:
            self._set_jira_project(requirement)
        return requirements

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
