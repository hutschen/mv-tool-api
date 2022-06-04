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

from sys import prefix
from requests import session
from sqlmodel import SQLModel, Session, select, Field
from fastapi import APIRouter, Depends, HTTPException
from fastapi_utils.cbv import cbv
from ..database import get_session

class ProjectInput(SQLModel):
    name: str
    description: str | None = None
    jira_project_id: str | None = None

class Project(ProjectInput, table=True):
    id: int | None = Field(default=None, primary_key=True)

project_router = APIRouter()
@cbv(project_router)
class ProjectsView:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    @project_router.get('/', response_model=list[Project], tags=['project'])
    def list_projects(self) -> list[Project]:
        query = select(Project)
        return self.session.exec(query).all()

    @project_router.post(
        '/', status_code=201, response_model=Project, tags=['project'])
    def create_project(self, project: ProjectInput) -> Project:
        new_project = Project.from_orm(project)
        self.session.add(new_project)
        self.session.commit()
        self.session.refresh(new_project)
        return new_project

    @project_router.get(
        '/{project_id}', response_model=Project, tags=['project'])
    def get_project(self, project_id: int) -> Project:
        project = self.session.get(Project, project_id)
        if project:
            return project
        else:
            raise HTTPException(404, f'No project with id={id}.')
    
    @project_router.put(
        '/{project_id}', response_model=Project, tags=['project'])
    def update_project(
            self, project_id: int, project_update: ProjectInput) -> Project:
        project_update = Project.from_orm(project_update)  
        project = self.get_project(project_id)
        project_update.id = project.id
        self.session.merge(project_update)
        self.session.commit()
        return project

    @project_router.delete('/{project_id}', status_code=204)
    def delete_project(self, project_id: int):
        project = self.get_project(project_id)
        self.session.delete(project)
        self.session.commit()
