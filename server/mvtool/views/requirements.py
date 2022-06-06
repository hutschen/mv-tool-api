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
from sqlmodel import Session
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv

from ..auth import get_jira
from ..database import CRUDMixin, get_session
from .projects import ProjectsView
from ..models import RequirementInput, Requirement, Project

router = APIRouter()


@cbv(router)
class RequirementsView(CRUDMixin[Requirement]):
    kwargs = dict(tags=['requirement'])

    def __init__(self, 
            session: Session = Depends(get_session),
            jira: JIRA = Depends(get_jira)):
        self.session = session
        self.projects = ProjectsView(session, jira)

    @router.get(
        '/projects/{project_id}/requirements', 
        response_model=list[Requirement], **kwargs)
    def list_requirements(self, project_id: int) -> list[Requirement]:
        return self._read_all_from_db(Requirement, project_id=project_id)

    @router.post(
        '/projects/{project_id}/requirements', status_code=201, 
        response_model=Requirement, **kwargs)
    def create_requirement(
            self, project_id: int, 
            requirement: RequirementInput) -> Requirement:
        project = self.projects.get_project(project_id)
        requirement = Requirement(**requirement.dict())
        self._create_in_db(requirement)
        requirement.project = project
        self.session.commit()
        self.session.refresh(requirement)
        return requirement

    @router.get(
        '/requirements/{requirement_id}', response_model=Requirement, **kwargs)
    def get_requirement(self, requirement_id: int) -> Requirement:
        return self._read_from_db(Requirement, requirement_id)

    @router.put(
        '/requirements/{requirement_id}', response_model=Requirement, **kwargs)
    def update_requirement(
            self, requirement_id: int, 
            requirement_update: RequirementInput) -> Requirement:
        requirement_update = Requirement.from_orm(requirement_update)
        return self._update_in_db(requirement_update)

    @router.delete(
        '/requirements/{requirement_id}', status_code=204, **kwargs)
    def delete_requirement(self, requirement_id: int) -> None:
        return self._delete_in_db(Requirement, requirement_id)