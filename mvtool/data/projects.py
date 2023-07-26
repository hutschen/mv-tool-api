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

from typing import Any, Iterable

from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select, select

from ..db.database import delete_from_db, get_session, read_from_db
from ..db.schema import Project
from ..models.projects import ProjectImport, ProjectInput, ProjectPatch
from ..utils.errors import NotFoundError
from ..utils.iteration import CachedIterable
from ..utils.models import field_is_set
from .jira_ import JiraProjects


class Projects:
    def __init__(
        self,
        jira_projects: JiraProjects = Depends(JiraProjects),
        session: Session = Depends(get_session),
    ):
        self._jira_projects = jira_projects
        self._session = session

    @staticmethod
    def _modify_projects_query(
        query: Select,
        where_clauses: list[Any] | None = None,
        order_by_clauses: list[Any] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Select:
        """Modify a query to include all required clauses and offset and limit."""
        if where_clauses:
            query = query.where(*where_clauses)
        if order_by_clauses:
            query = query.order_by(*order_by_clauses)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query

    def list_projects(
        self,
        where_clauses: list[Any] | None = None,
        order_by_clauses: list[Any] | None = None,
        offset: int | None = None,
        limit: int | None = None,
        query_jira: bool = True,
    ) -> list[Project]:
        # Construct projects query
        query = self._modify_projects_query(
            select(Project),
            where_clauses,
            order_by_clauses or [Project.id],
            offset,
            limit,
        )

        # Execute projects query
        projects: list[Project] = self._session.execute(query).scalars().all()

        # set jira projects on projects
        if query_jira:
            jira_projects_cached = False
            for project in projects:
                if project.jira_project_id and not jira_projects_cached:
                    # cache jira projects
                    list(self._jira_projects.list_jira_projects())
                    jira_projects_cached = True

                self._set_jira_project(project, try_to_get=False)

        return projects

    def count_projects(self, where_clauses: list[Any] | None = None) -> int:
        query = self._modify_projects_query(
            select(func.count()).select_from(Project), where_clauses
        )
        return self._session.execute(query).scalar()

    def has_project(self, where_clauses: list[Any] | None = None) -> bool:
        query = self._modify_projects_query(select(Project), where_clauses).exists()
        return self._session.query(query).scalar()

    def create_project(
        self, creation: ProjectInput | ProjectImport, skip_flush: bool = False
    ) -> Project:
        project = Project(**creation.model_dump(exclude={"id", "jira_project"}))

        try_to_get_jira_project = True
        if isinstance(creation, ProjectInput):
            # check jira project id and cache load jira project
            self._jira_projects.check_jira_project_id(project.jira_project_id)
            try_to_get_jira_project = False  # already loaded

        self._session.add(project)
        if not skip_flush:
            self._session.flush()

        self._set_jira_project(project, try_to_get=try_to_get_jira_project)
        return project

    def get_project(self, project_id: int) -> Project:
        project = read_from_db(self._session, Project, project_id)
        self._set_jira_project(project)
        return project

    def update_project(
        self,
        project: Project,
        update: ProjectInput | ProjectImport,
        patch: bool = False,
        skip_flush: bool = False,
    ) -> None:
        try_to_get_jira_project = True
        if isinstance(update, ProjectInput):
            # check jira project id and cache load jira project
            if update.jira_project_id != project.jira_project_id:
                self._jira_projects.check_jira_project_id(update.jira_project_id)
                try_to_get_jira_project = False  # already loaded

        # update project
        for key, value in update.model_dump(
            exclude_unset=patch, exclude={"id", "jira_project"}
        ).items():
            setattr(project, key, value)

        if not skip_flush:
            self._session.flush()

        self._set_jira_project(project, try_to_get=try_to_get_jira_project)

    def patch_project(
        self,
        project: Project,
        patch: ProjectPatch,
        skip_flush: bool = False,
    ) -> None:
        try_to_get_jira_project = True
        for key, value in patch.model_dump(exclude_unset=True).items():
            if key == "jira_project_id":
                # check jira project id and cache load jira project
                self._jira_projects.check_jira_project_id(value)
                try_to_get_jira_project = False  # already loaded

            setattr(project, key, value)

        if not skip_flush:
            self._session.flush()

        self._set_jira_project(project, try_to_get=try_to_get_jira_project)

    def delete_project(self, project: Project, skip_flush: bool = False) -> None:
        return delete_from_db(self._session, project, skip_flush)

    def bulk_create_update_projects(
        self,
        project_imports: Iterable[ProjectImport],
        patch: bool = False,
        skip_flush: bool = False,
    ):
        project_imports = CachedIterable(project_imports)

        # Get projects to be updated from the database
        ids = [p.id for p in project_imports if p.id is not None]
        projects_to_update = {
            p.id: p for p in (self.list_projects([Project.id.in_(ids)]) if ids else [])
        }

        # Cache jira projects
        jira_projects_map = {
            jp.key: jp for jp in self._jira_projects.list_jira_projects()
        }

        # Create or update projects
        for project_import in project_imports:
            if project_import.id is None:
                # Create project
                project = self.create_project(project_import, skip_flush=True)
            else:
                # Update project
                project = projects_to_update.get(project_import.id)
                if project is None:
                    raise NotFoundError(f"No project with id={project_import.id}.")
                self.update_project(project, project_import, patch, skip_flush=True)

            # Set jira project
            if field_is_set(project_import, "jira_project") or not patch:
                jira_project = None
                if project_import.jira_project is not None:
                    jira_project = jira_projects_map.get(
                        project_import.jira_project.key
                    )
                    if jira_project is None:
                        raise NotFoundError(
                            f"No Jira project with key={project_import.jira_project.key}."
                        )
                project.jira_project_id = jira_project.id if jira_project else None

            yield project

        if not skip_flush:
            self._session.flush()

    def convert_project_imports(
        self, project_imports: Iterable[ProjectImport], patch: bool = False
    ) -> dict[str, Project]:
        # Map project imports to their etags
        projects_map = {p.etag: p for p in project_imports}

        # Map created and updated projects to the etags of their imports
        for etag, project in zip(
            projects_map.keys(),
            self.bulk_create_update_projects(
                projects_map.values(), patch=patch, skip_flush=True
            ),
        ):
            projects_map[etag] = project

        return projects_map

    def _set_jira_project(self, project: Project, try_to_get: bool = True) -> None:
        project._get_jira_project = (
            lambda jira_project_id: self._jira_projects.lookup_jira_project(
                jira_project_id, try_to_get
            )
        )
