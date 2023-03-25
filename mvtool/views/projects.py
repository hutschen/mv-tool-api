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

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import constr
from sqlmodel import Column, Session, func, or_, select
from sqlmodel.sql.expression import Select

from ..database import delete_from_db, get_session, read_from_db
from ..models.projects import (
    Project,
    ProjectImport,
    ProjectInput,
    ProjectOutput,
    ProjectRepresentation,
)
from ..utils.errors import NotFoundError
from ..utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
    search_columns,
)
from ..utils.iteration import CachedIterable
from ..utils.models import field_is_set
from ..utils.pagination import Page, page_params
from .jira_ import JiraProjectsView

router = APIRouter()


class ProjectsView:
    kwargs = dict(tags=["project"])

    def __init__(
        self,
        jira_projects: JiraProjectsView = Depends(JiraProjectsView),
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
        projects: list[Project] = self._session.exec(query).all()

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
            select([func.count()]).select_from(Project), where_clauses
        )
        return self._session.execute(query).scalar()

    def create_project(
        self, creation: ProjectInput | ProjectImport, skip_flush: bool = False
    ) -> Project:
        project = Project(**creation.dict(exclude={"id", "jira_project"}))

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
        for key, value in update.dict(
            exclude_unset=patch, exclude={"id", "jira_project"}
        ).items():
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
            # Get jira project
            jira_project = None
            if project_import.jira_project is not None:
                jira_project = jira_projects_map.get(project_import.jira_project.key)
                if jira_project is None:
                    raise NotFoundError(
                        f"No Jira project with key={project_import.jira_project.key}."
                    )

            if project_import.id is None:
                # Create project
                project = self.create_project(project_import, skip_flush=True)
            else:
                # Update project
                project = projects_to_update.get(project_import.id)
                if project is None:
                    raise NotFoundError(f"No project with id={project_import.id}.")
                self.update_project(project, project_import, patch, skip_flush=True)

            if field_is_set(project_import, "jira_project") or not patch:
                project.jira_project_id = jira_project.id if jira_project else None
            yield project

        if not skip_flush:
            self._session.flush()

    def _set_jira_project(self, project: Project, try_to_get: bool = True) -> None:
        project._get_jira_project = (
            lambda jira_project_id: self._jira_projects.lookup_jira_project(
                jira_project_id, try_to_get
            )
        )


def get_project_filters(
    # filter by pattern
    name: str | None = None,
    description: str | None = None,
    #
    # filter by ids
    ids: list[int] | None = Query(None),
    jira_project_ids: list[str] | None = Query(None),
    #
    # filter for existence
    has_description: bool | None = None,
    has_jira_project: bool | None = None,
    #
    # filter by search string
    search: str | None = None,
) -> list[Any]:
    where_clauses = []

    # filter by pattern
    for column, value in [
        (Project.name, name),
        (Project.description, description),
    ]:
        if value is not None:
            where_clauses.append(filter_by_pattern(column, value))

    # filter by ids
    for column, values in (
        (Project.id, ids),
        (Project.jira_project_id, jira_project_ids),
    ):
        if values:
            where_clauses.append(filter_by_values(column, values))

    # filter for existence
    for column, value in [
        (Project.description, has_description),
        (Project.jira_project_id, has_jira_project),
    ]:
        if value is not None:
            where_clauses.append(filter_for_existence(column, value))

    # filter by search string
    if search:
        where_clauses.append(
            or_(
                filter_by_pattern(column, f"*{search}*")
                for column in (Project.name, Project.description)
            )
        )

    return where_clauses


def get_project_sort(
    sort_by: str | None = None, sort_order: constr(regex=r"^(asc|desc)$") | None = None
) -> list[Any]:
    if not (sort_by and sort_order):
        return []

    try:
        columns: list[Column] = {
            "name": [Project.name],
            "description": [Project.description],
            "jira_project": [Project.jira_project_id],
        }[sort_by]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by parameter: {sort_by}",
        )

    columns.append(Project.id)
    if sort_order == "asc":
        return [column.asc() for column in columns]
    else:
        return [column.desc() for column in columns]


@router.get(
    "/projects",
    response_model=Page[ProjectOutput] | list[ProjectOutput],
    **ProjectsView.kwargs,
)
def get_projects(
    where_clauses=Depends(get_project_filters),
    order_by_clauses=Depends(get_project_sort),
    page_params=Depends(page_params),
    projects_view: ProjectsView = Depends(),
):
    projects = projects_view.list_projects(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        projects_count = projects_view.count_projects(where_clauses)
        return Page[ProjectOutput](items=projects, total_count=projects_count)
    else:
        return projects


@router.post(
    "/projects", status_code=201, response_model=ProjectOutput, **ProjectsView.kwargs
)
def create_project(
    project: ProjectInput, projects_view: ProjectsView = Depends()
) -> Project:
    return projects_view.create_project(project)


@router.get(
    "/projects/{project_id}", response_model=ProjectOutput, **ProjectsView.kwargs
)
def get_project(project_id: int, projects_view: ProjectsView = Depends()) -> Project:
    return projects_view.get_project(project_id)


@router.put(
    "/projects/{project_id}", response_model=ProjectOutput, **ProjectsView.kwargs
)
def update_project(
    project_id: int,
    project_input: ProjectInput,
    projects_view: ProjectsView = Depends(),
) -> Project:
    project = projects_view.get_project(project_id)
    projects_view.update_project(project, project_input)
    return project


@router.delete("/projects/{project_id}", status_code=204, **ProjectsView.kwargs)
def delete_project(project_id: int, projects_view: ProjectsView = Depends()) -> None:
    project = projects_view.get_project(project_id)
    projects_view.delete_project(project)


@router.get(
    "/project/representations",
    response_model=Page[ProjectRepresentation] | list[ProjectRepresentation],
    **ProjectsView.kwargs,
)
def get_project_representations(
    where_clauses: list[Any] = Depends(get_project_filters),
    local_search: str | None = None,
    order_by_clauses=Depends(get_project_sort),
    page_params=Depends(page_params),
    projects_view: ProjectsView = Depends(),
):
    if local_search:
        where_clauses.append(search_columns(local_search, Project.name))

    projects = projects_view.list_projects(
        where_clauses, order_by_clauses, **page_params, query_jira=False
    )
    if page_params:
        projects_count = projects_view.count_projects(where_clauses)
        return Page[ProjectRepresentation](items=projects, total_count=projects_count)
    else:
        return projects


@router.get(
    "/project/field-names",
    response_model=list[str],
    **ProjectsView.kwargs,
)
def get_project_field_names(
    where_clauses=Depends(get_project_filters),
    projects_view: ProjectsView = Depends(),
) -> set[str]:
    field_names = {"id", "name"}
    for field, names in [
        (Project.description, ["description"]),
        (Project.jira_project_id, ["jira_project"]),
    ]:
        if projects_view.count_projects(
            [filter_for_existence(field, True), *where_clauses]
        ):
            field_names.update(names)
    return field_names
