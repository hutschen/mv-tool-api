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

from jira import JIRA
from sqlmodel import Relationship, SQLModel, Session, Field
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv

from ..auth import get_jira
from ..database import CRUDMixin, get_session
from .jira_ import JiraProjectsView
from ..models import ProjectInput, Project

router = APIRouter()


@cbv(router)
class ProjectsView(CRUDMixin[Project]):
    kwargs = dict(tags=['project'])

    def __init__(self, 
            session: Session = Depends(get_session), jira: JIRA = Depends(get_jira)):
        self.session = session
        self.jira_projects = JiraProjectsView(jira)

    @router.get('/projects', response_model=list[Project], **kwargs)
    def list_projects(self) -> list[Project]:
        return self._read_all_from_db(Project)

    @router.post('/projects', status_code=201, response_model=Project, **kwargs)
    def create_project(self, new_project: ProjectInput) -> Project:
        new_project = Project.from_orm(new_project)
        self.jira_projects.check_project_id(new_project.jira_project_id)
        return self._create_in_db(new_project)

    @router.get('/projects/{project_id}', response_model=Project, **kwargs)
    def get_project(self, project_id: int) -> Project:
        return self._read_from_db(Project, project_id)
    
    @router.put('/projects/{project_id}', response_model=Project, **kwargs)
    def update_project(
            self, project_id: int, project_update: ProjectInput) -> Project:
        project_update = Project.from_orm(project_update)
        project_current = self.get_project(project_id)

        if project_update.jira_project_id != project_current.jira_project_id:
            self.jira_projects.check_project_id(project_update.jira_project_id)
        
        return self._update_in_db(project_id, project_update)

    @router.delete('/projects/{project_id}', status_code=204, **kwargs)
    def delete_project(self, project_id: int):
        return self._delete_in_db(Project, project_id)
