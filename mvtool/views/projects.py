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
from fastapi import APIRouter, Depends, Query
from fastapi_utils.cbv import cbv
from sqlmodel import or_

from mvtool.utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
)

from ..errors import NotFoundError
from ..database import CRUDOperations
from .jira_ import JiraProjectsView
from ..models import ProjectInput, Project, ProjectOutput

router = APIRouter()


@cbv(router)
class ProjectsView:
    kwargs = dict(tags=["project"])

    def __init__(
        self,
        jira_projects: JiraProjectsView = Depends(JiraProjectsView),
        crud: CRUDOperations[Project] = Depends(CRUDOperations),
    ):
        self._jira_projects = jira_projects
        self._crud = crud
        self._session = self._crud.session

    @router.get("/projects", response_model=list[ProjectOutput], **kwargs)
    def list_projects(self) -> Iterator[Project]:
        jira_projects_cached = False

        for project in self._crud.read_all_from_db(Project):
            if not jira_projects_cached:
                list(self._jira_projects.list_jira_projects())
                jira_projects_cached = True

            self._set_jira_project(project, try_to_get=False)
            yield project

    @router.post("/projects", status_code=201, response_model=ProjectOutput, **kwargs)
    def create_project(self, project_input: ProjectInput) -> Project:
        self._jira_projects.check_jira_project_id(project_input.jira_project_id)
        project = self._crud.create_in_db(Project.from_orm(project_input))
        self._set_jira_project(project, try_to_get=False)
        return project

    @router.get("/projects/{project_id}", response_model=ProjectOutput, **kwargs)
    def get_project(self, project_id: int) -> Project:
        project = self._crud.read_from_db(Project, project_id)
        self._set_jira_project(project)
        return project

    @router.put("/projects/{project_id}", response_model=ProjectOutput, **kwargs)
    def update_project(self, project_id: int, project_input: ProjectInput) -> Project:
        project = self._session.get(Project, project_id)
        if not project:
            cls_name = Project.__name__
            raise NotFoundError(f"No {cls_name} with id={project_id}.")

        # check jira project id and cache loaded jira project
        if project_input.jira_project_id != project.jira_project_id:
            self._jira_projects.check_jira_project_id(project_input.jira_project_id)

        # update project in database
        for key, value in project_input.dict().items():
            setattr(project, key, value)
        self._session.flush()

        self._set_jira_project(project)
        return project

    @router.delete("/projects/{project_id}", status_code=204, **kwargs)
    def delete_project(self, project_id: int):
        return self._crud.delete_from_db(Project, project_id)

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
    jira_project_ids: list[str] | None = Query(None),
    #
    # filter for existence
    has_name: bool | None = None,
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

    # filter by Jira project ids
    if jira_project_ids:
        where_clauses.append(
            filter_by_values(Project.jira_project_id, jira_project_ids)
        )

    # filter for existence
    for column, value in [
        (Project.name, has_name),
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
                for column in (
                    Project.name,
                    Project.description,
                )
            )
        )

    return where_clauses
