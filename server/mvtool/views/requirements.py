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
from sqlmodel import Relationship, SQLModel, Field, Session, select
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv

from ..auth import get_jira
from ..database import CRUDMixin, get_session
from .projects import Project, ProjectsView

router = APIRouter()


class RequirementInput(SQLModel):
    reference: str | None
    summary: str
    description: str | None
    target_object: str | None
    compliance_status: str | None
    compliance_comment: str | None
    project_id: int = Field(foreign_key='project.id')


class Requirement(RequirementInput, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project: Project = Relationship(back_populates='requirements')


@cbv(router)
class RequirementsView(CRUDMixin[Requirement]):
    kwargs = dict(tags=['requirement'])

    def __init__(self, 
            session: Session = Depends(get_session),
            jira: JIRA = Depends(get_jira)):
        self.session = session
        self.projects = ProjectsView(session, jira)

    @router.get('/', response_model=list[Requirement], **kwargs)
    def list_requirements(self, project_id: int) -> list[Requirement]:
        return self._read_all_from_db(Requirement, project_id=project_id)

    @router.post('/', status_code=201, response_model=Requirement, **kwargs)
    def create_requirement(
            self, new_requirement: RequirementInput) -> Requirement:
        new_requirement = Requirement.from_orm(new_requirement)
        new_requirement.project = self.projects.get_project(
            new_requirement.project_id)
        return self._create_in_db(new_requirement)