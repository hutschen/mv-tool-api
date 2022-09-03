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


from typing import Iterator
from fastapi import APIRouter, Depends, Response
from fastapi_utils.cbv import cbv

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

    @router.get("/projects", response_model=list[ProjectOutput], **kwargs)
    def _list_projects(self) -> Iterator[ProjectOutput]:
        jira_projects_map = {
            jp.id: jp for jp in self._jira_projects.list_jira_projects()
        }
        for project in self.list_projects():
            project = ProjectOutput.from_orm(project)
            try:
                project.jira_project = jira_projects_map[project.jira_project_id]
            except KeyError:
                pass
            yield project

    def list_projects(self) -> list[Project]:
        return self._crud.read_all_from_db(Project)

    @router.post("/projects", status_code=201, response_model=ProjectOutput, **kwargs)
    def _create_project(self, project: ProjectInput) -> ProjectOutput:
        project = ProjectOutput.from_orm(self.create_project(project))
        project.jira_project = self._jira_projects.try_to_get_jira_project(
            project.jira_project_id
        )
        return project

    def create_project(self, new_project: ProjectInput) -> Project:
        new_project = Project.from_orm(new_project)
        self._jira_projects.check_jira_project_id(new_project.jira_project_id)
        return self._crud.create_in_db(new_project)

    @router.get("/projects/{project_id}", response_model=ProjectOutput, **kwargs)
    def _get_project(self, project_id: int) -> ProjectOutput:
        project = ProjectOutput.from_orm(self.get_project(project_id))
        project.jira_project = self._jira_projects.try_to_get_jira_project(
            project.jira_project_id
        )
        return project

    def get_project(self, project_id: int) -> Project:
        return self._crud.read_from_db(Project, project_id)

    @router.put("/projects/{project_id}", response_model=ProjectOutput, **kwargs)
    def _update_project(
        self, project_id: int, project_update: ProjectInput
    ) -> ProjectOutput:
        project = ProjectOutput.from_orm(
            self.update_project(project_id, project_update)
        )
        project.jira_project = self._jira_projects.try_to_get_jira_project(
            project.jira_project_id
        )
        return project

    def update_project(self, project_id: int, project_update: ProjectInput) -> Project:
        project_update = Project.from_orm(project_update)
        project_current = self.get_project(project_id)
        if project_update.jira_project_id != project_current.jira_project_id:
            self._jira_projects.check_jira_project_id(project_update.jira_project_id)
        return self._crud.update_in_db(project_id, project_update)

    @router.delete(
        "/projects/{project_id}", status_code=204, response_class=Response, **kwargs
    )
    def delete_project(self, project_id: int):
        return self._crud.delete_from_db(Project, project_id)
