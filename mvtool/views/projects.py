# coding: utf-8
# 
# Copyright 2022 Helmar Hutschenreuter
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation. You may obtain
# a copy of the GNU AGPL V3 at https://www.gnu.org/licenses/.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AGPL V3 for more details.

from typing import Iterator
from jira import JIRA, JIRAError
import jira
from sqlmodel import Session
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv

from ..auth import get_jira
from ..database import CRUDOperations, get_session
from .jira_ import JiraProjectsView
from ..models import ProjectInput, Project, ProjectOutput

router = APIRouter()


@cbv(router)
class ProjectsView(CRUDOperations[Project]):
    kwargs = dict(tags=['project'])

    def __init__(self, 
            session: Session = Depends(get_session), jira: JIRA = Depends(get_jira)):
        super().__init__(session, Project)
        self.jira_projects = JiraProjectsView(jira)

    @router.get('/projects', response_model=list[ProjectOutput], **kwargs)
    def _list_projects(self) -> Iterator[ProjectOutput]:
        jira_projects_map = {
            jp.id:jp for jp in self.jira_projects.list_jira_projects()}
        for project in self.list_projects():
            project = ProjectOutput.from_orm(project)
            try:
                project.jira_project = \
                    jira_projects_map[project.jira_project_id]
            except KeyError:
                pass
            yield project

    def list_projects(self) -> list[Project]:
        return self.read_all_from_db()

    @router.post(
        '/projects', status_code=201, response_model=ProjectOutput, **kwargs)
    def _create_project(self, new_project: ProjectInput) -> ProjectOutput:
        new_project = Project.from_orm(new_project)
        if new_project.jira_project_id is not None:
            jira_project = self.jira_projects.get_jira_project(
                new_project.jira_project_id)
        else:
            jira_project = None
        new_project = ProjectOutput.from_orm(self.create_in_db(new_project))
        new_project.jira_project = jira_project
        return new_project

    def create_project(self, new_project: ProjectInput) -> Project:
        new_project = Project.from_orm(new_project)
        self.jira_projects.check_jira_project_id(new_project.jira_project_id)
        return self.create_in_db(new_project)

    @router.get(
        '/projects/{project_id}', response_model=ProjectOutput, **kwargs)
    def _get_project(
            self, project_id: int) -> ProjectOutput:
        project = ProjectOutput.from_orm(self.get_project(project_id))
        project.jira_project = self.jira_projects.try_to_get_jira_project(
            project.jira_project_id)
        return project

    def get_project(self, project_id: int) -> Project:
        return self.read_from_db(project_id)
    
    @router.put(
        '/projects/{project_id}', response_model=ProjectOutput, **kwargs)
    def _update_project(
            self, project_id: int, 
            project_update: ProjectInput) -> ProjectOutput:
        project_update = Project.from_orm(project_update)
        project_current = self.get_project(project_id)

        if project_update.jira_project_id is None:
            jira_project = None
        elif project_update.jira_project_id != project_current.jira_project_id:
            jira_project = self.jira_projects.get_jira_project(
                project_update.jira_project_id)
        else:
            jira_project = self.jira_projects.try_to_get_jira_project(
                project_update.jira_project_id)
        
        project = ProjectOutput.from_orm(
            self.update_in_db(project_id, project_update))
        project.jira_project = jira_project
        return project

    def update_project(
            self, project_id: int, project_update: ProjectInput) -> Project:
        project_update = Project.from_orm(project_update)
        project_current = self.get_project(project_id)
        if project_update.jira_project_id != project_current.jira_project_id:
            self.jira_projects.check_jira_project_id(
                project_update.jira_project_id)
        return self.update_in_db(project_id, project_update)

    @router.delete('/projects/{project_id}', status_code=204, **kwargs)
    def delete_project(self, project_id: int):
        return self.delete_in_db(project_id)
