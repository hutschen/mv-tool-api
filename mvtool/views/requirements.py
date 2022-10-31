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

from mvtool.errors import NotFoundError
from mvtool.views.jira_ import JiraProjectsView

from ..database import CRUDOperations
from .projects import ProjectsView
from ..models import RequirementInput, Requirement, RequirementOutput

router = APIRouter()


@cbv(router)
class RequirementsView:
    kwargs = dict(tags=["requirement"])

    def __init__(
        self,
        projects: ProjectsView = Depends(ProjectsView),
        crud: CRUDOperations[Requirement] = Depends(CRUDOperations),
    ):
        self._projects = projects
        self._crud = crud
        self._session = self._crud.session

    @router.get(
        "/projects/{project_id}/requirements",
        response_model=list[RequirementOutput],
        **kwargs,
    )
    def list_requirements(self, project_id: int) -> Iterator[Requirement]:
        project = self._projects.get_project(project_id)
        for requirement in self._crud.read_all_from_db(
            Requirement, project_id=project_id
        ):
            requirement.project._jira_project = project.jira_project
            yield requirement

    @router.post(
        "/projects/{project_id}/requirements",
        status_code=201,
        response_model=RequirementOutput,
        **kwargs,
    )
    def create_requirement(
        self, project_id: int, requirement_input: RequirementInput
    ) -> Requirement:
        requirement = Requirement.from_orm(requirement_input)
        requirement.project = self._projects.get_project(project_id)
        return self._crud.create_in_db(requirement)

    @router.get(
        "/requirements/{requirement_id}", response_model=RequirementOutput, **kwargs
    )
    def get_requirement(self, requirement_id: int) -> Requirement:
        requirement = self._crud.read_from_db(Requirement, requirement_id)
        self._projects._set_jira_project(requirement.project)
        return requirement

    @router.put(
        "/requirements/{requirement_id}", response_model=RequirementOutput, **kwargs
    )
    def update_requirement(
        self, requirement_id: int, requirement_input: RequirementInput
    ) -> Requirement:
        requirement = self._session.get(Requirement, requirement_id)
        if not requirement:
            cls_name = Requirement.__name__
            raise NotFoundError(f"No {cls_name} with id={requirement_id}.")

        for key, value in requirement_input.dict().items():
            setattr(requirement, key, value)
        self._session.flush()

        self._projects._set_jira_project(requirement.project)
        return requirement

    @router.delete("/requirements/{requirement_id}", status_code=204, **kwargs)
    def delete_requirement(self, requirement_id: int) -> None:
        return self._crud.delete_from_db(Requirement, requirement_id)
