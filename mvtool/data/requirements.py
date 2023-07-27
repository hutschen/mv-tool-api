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

from fastapi import Depends
from sqlalchemy import Column, func
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select, select

from ..db.database import delete_from_db, get_session, read_from_db
from ..db.schema import Catalog, CatalogModule, CatalogRequirement, Project, Requirement
from ..models.requirements import RequirementImport, RequirementInput, RequirementPatch
from ..utils.errors import NotFoundError
from ..utils.etag_map import get_from_etag_map
from ..utils.fallback import fallback
from ..utils.filtering import filter_for_existence
from ..utils.iteration import CachedIterable
from ..utils.models import field_is_set
from .catalog_requirements import CatalogRequirements
from .projects import Projects


class Requirements:
    def __init__(
        self,
        projects: Projects = Depends(Projects),
        catalog_requirements: CatalogRequirements = Depends(CatalogRequirements),
        session: Session = Depends(get_session),
    ):
        self._projects = projects
        self._catalog_requirements = catalog_requirements
        self._session = session

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
            select(Requirement),
            where_clauses,
            order_by_clauses or [Requirement.id.asc()],
            offset,
            limit,
        )

        # execute query, set jira_project and return requirements
        requirements = self._session.execute(query).scalars().all()
        if query_jira:
            for requirement in requirements:
                self._set_jira_project(requirement)
        return requirements

    def count_requirements(self, where_clauses: Any = None) -> int:
        query = self._modify_requirements_query(
            select(func.count()).select_from(Requirement), where_clauses
        )
        return self._session.execute(query).scalar()

    def has_requirement(self, where_clauses: Any = None) -> bool:
        query = self._modify_requirements_query(
            select(Requirement), where_clauses
        ).exists()
        return self._session.query(query).scalar()

    def list_requirement_values(
        self,
        column: Column,
        where_clauses: Any = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        query = self._modify_requirements_query(
            select(func.distinct(column)).select_from(Requirement),
            [filter_for_existence(column), *(where_clauses or [])],
            offset=offset,
            limit=limit,
        )
        return self._session.execute(query).scalars().all()

    def count_requirement_values(
        self, column: Column, where_clauses: Any = None
    ) -> int:
        query = self._modify_requirements_query(
            select(func.count(func.distinct(column))).select_from(Requirement),
            [filter_for_existence(column), *(where_clauses or [])],
        )
        return self._session.execute(query).scalar()

    def create_requirement(
        self,
        project: Project,
        creation: RequirementInput | RequirementImport,
        skip_flush: bool = False,
    ) -> Requirement:
        requirement = Requirement(
            **creation.model_dump(exclude={"id", "project", "catalog_requirement"})
        )
        self._session.add(requirement)
        requirement.project = project

        # check catalog_requirement_id and set catalog_requirement
        if isinstance(creation, RequirementInput):
            requirement.catalog_requirement = (
                self._catalog_requirements.check_catalog_requirement_id(
                    creation.catalog_requirement_id
                )
            )

        if not skip_flush:
            self._session.flush()
        return requirement

    def get_requirement(self, requirement_id: int) -> Requirement:
        requirement = read_from_db(self._session, Requirement, requirement_id)
        self._set_jira_project(requirement)
        return requirement

    def update_requirement(
        self,
        requirement: Requirement,
        update: RequirementInput | RequirementImport,
        patch: bool = False,
        skip_flush: bool = False,
    ) -> None:
        for key, value in update.model_dump(
            exclude_unset=patch, exclude={"id", "project", "catalog_requirement"}
        ).items():
            setattr(requirement, key, value)

        # check catalog_requirement_id and set catalog_requirement
        if isinstance(update, RequirementInput):
            requirement.catalog_requirement = (
                self._catalog_requirements.check_catalog_requirement_id(
                    update.catalog_requirement_id
                )
            )

        if not skip_flush:
            self._session.flush()

    def patch_requirement(
        self,
        requirement: Requirement,
        patch: RequirementPatch,
        skip_flush: bool = False,
    ) -> None:
        for key, value in patch.model_dump(exclude_unset=True).items():
            setattr(requirement, key, value)
        if not skip_flush:
            self._session.flush()

    def delete_requirement(
        self, requirement: Requirement, skip_flush: bool = False
    ) -> None:
        return delete_from_db(self._session, requirement, skip_flush)

    def bulk_create_update_requirements(
        self,
        requirement_imports: Iterable[RequirementImport],
        fallback_project: Project | None = None,
        fallback_catalog_module: CatalogModule | None = None,
        patch: bool = False,
        skip_flush: bool = False,
    ) -> Iterator[Requirement]:
        requirement_imports = CachedIterable(requirement_imports)

        # Convert project imports to projects
        projects_map = self._projects.convert_project_imports(
            (r.project for r in requirement_imports if r.project is not None),
            patch=patch,
        )

        # Convert catalog requirement imports to catalog requirements
        catalog_requirements_map = (
            self._catalog_requirements.convert_catalog_requirement_imports(
                (
                    r.catalog_requirement
                    for r in requirement_imports
                    if r.catalog_requirement is not None
                ),
                fallback_catalog_module,
                patch=patch,
            )
        )

        # Get requirements to be updated from database
        ids = [r.id for r in requirement_imports if r.id is not None]
        requirements_to_update = {
            r.id: r
            for r in (self.list_requirements([Requirement.id.in_(ids)]) if ids else [])
        }

        # Create or update requirements
        for requirement_import in requirement_imports:
            project = get_from_etag_map(projects_map, requirement_import.project)

            if requirement_import.id is None:
                # Create requirement
                requirement = self.create_requirement(
                    fallback(
                        project, fallback_project, "No fallback project provided."
                    ),
                    requirement_import,
                    skip_flush=True,
                )
            else:
                # Update requirement
                requirement = requirements_to_update.get(requirement_import.id)
                if requirement is None:
                    raise NotFoundError(
                        f"No requirement with id={requirement_import.id}."
                    )
                self.update_requirement(
                    requirement, requirement_import, patch=patch, skip_flush=True
                )

            # Set catalog requirement
            if field_is_set(requirement_import, "catalog_requirement") or not patch:
                requirement.catalog_requirement = get_from_etag_map(
                    catalog_requirements_map, requirement_import.catalog_requirement
                )

            yield requirement

        if not skip_flush:
            self._session.flush()

    def convert_requirement_imports(
        self,
        requirement_imports: Iterable[RequirementImport],
        fallback_project: Project | None = None,
        fallback_catalog_module: CatalogModule | None = None,
        patch: bool = False,
    ) -> dict[str, Requirement]:
        # Map requirement imports to their etags
        requirements_map = {r.etag: r for r in requirement_imports}

        # Map created and updates requirements to the etag of their imports
        for etag, requirement in zip(
            requirements_map.keys(),
            self.bulk_create_update_requirements(
                requirements_map.values(),
                fallback_project,
                fallback_catalog_module,
                patch=patch,
                skip_flush=True,
            ),
        ):
            requirements_map[etag] = requirement

        return requirements_map

    def bulk_create_requirements_from_catalog_requirements(
        self,
        project: Project,
        catalog_requirements: Iterable[CatalogRequirement],
        skip_flush: bool = False,
    ) -> Iterator[Requirement]:
        for catalog_requirement in catalog_requirements:
            requirement = self.create_requirement(
                project,
                RequirementInput.model_validate(catalog_requirement),
                skip_flush=True,
            )
            requirement.catalog_requirement = catalog_requirement
            yield requirement

        if not skip_flush:
            self._session.flush()

    def _set_jira_project(
        self, requirement: Requirement, try_to_get: bool = True
    ) -> None:
        self._projects._set_jira_project(requirement.project, try_to_get)
