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

from sqlmodel import SQLModel, Session, Field
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from ..database import CRUDMixin, get_session

router = APIRouter()


class ProjectInput(SQLModel):
    name: str
    description: str | None = None
    jira_project_id: str | None = None


class Project(ProjectInput, table=True):
    id: int | None = Field(default=None, primary_key=True)

@cbv(router)
class ProjectsView(CRUDMixin[Project]):
    kwargs = dict(tags=['project'])

    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    @router.get('/', response_model=list[Project], **kwargs)
    def list_projects(self) -> list[Project]:
        return self._get_all_from_db(Project)

    @router.post('/', status_code=201, response_model=Project, **kwargs)
    def create_project(self, new_project: ProjectInput) -> Project:
        new_project = Project.from_orm(new_project)
        return self._create_in_db(new_project)

    @router.get('/{project_id}', response_model=Project, **kwargs)
    def get_project(self, project_id: int) -> Project:
        return self._get_from_db(Project, project_id)
    
    @router.put('/{project_id}', response_model=Project, **kwargs)
    def update_project(
            self, project_id: int, project_update: ProjectInput) -> Project:
        project_update = Project.from_orm(project_update)  
        return self._update_in_db(project_update)

    @router.delete('/{project_id}', status_code=204, **kwargs)
    def delete_project(self, project_id: int):
        return self._delete_in_db(Project, project_id)
