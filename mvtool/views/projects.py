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
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv

from ..errors import NotFoundError
from ..database import CRUDOperations
from .jira_ import JiraProjectsView
from ..models import JiraProject, ProjectInput, Project, ProjectOutput

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
        projects = self._crud.read_all_from_db(Project)
        jira_projects_map = {
            jp.id: jp for jp in self._jira_projects.list_jira_projects()
        }

        for project in projects:
            self._set_jira_project(
                project, jira_projects_map.get(project.jira_project_id, None)
            )
            yield project

    @router.post("/projects", status_code=201, response_model=ProjectOutput, **kwargs)
    def create_project(self, project_input: ProjectInput) -> Project:
        if project_input.jira_project_id is None:
            jira_project = None
        else:
            jira_project = self._jira_projects.get_jira_project(
                project_input.jira_project_id
            )

        project = self._crud.create_in_db(Project.from_orm(project_input))
        self._set_jira_project(project, jira_project)
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
            jira_project = self._jira_projects.get_jira_project(
                project_input.jira_project_id
            )
        else:
            jira_project = None

        # update project in database
        for key, value in project_input.dict().items():
            setattr(project, key, value)
        self._session.flush()

        self._set_jira_project(project, jira_project)
        return project

    @router.delete("/projects/{project_id}", status_code=204, **kwargs)
    def delete_project(self, project_id: int):
        return self._crud.delete_from_db(Project, project_id)

    def _set_jira_project(
        self, project: Project, jira_project: JiraProject | None = None
    ) -> None:
        project._jira_project = jira_project
        project._get_jira_project = self._jira_projects.try_to_get_jira_project
