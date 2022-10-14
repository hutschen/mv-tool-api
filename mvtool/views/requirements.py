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
from sqlmodel import select

from ..database import CRUDOperations
from .projects import ProjectsView
from .catalog_modules import CatalogModulesView
from ..models import RequirementInput, Requirement, RequirementOutput

router = APIRouter()


@cbv(router)
class RequirementsView:
    kwargs = dict(tags=["requirement"])

    def __init__(
        self,
        projects: ProjectsView = Depends(ProjectsView),
        catalog_modules: CatalogModulesView = Depends(CatalogModulesView),
        crud: CRUDOperations[Requirement] = Depends(CRUDOperations),
    ):
        self._projects = projects
        self._catalog_modules = catalog_modules
        self._crud = crud
        self._session = self._crud.session

    @router.get(
        "/projects/{project_id}/requirements",
        response_model=list[RequirementOutput],
        **kwargs
    )
    def _list_requirements(self, project_id: int) -> Iterator[RequirementOutput]:
        # TODO: rename route to list_project_requirements
        project_output = self._projects._get_project(project_id)
        for requirement in self.list_requirements(project_id):
            yield RequirementOutput.from_orm(
                requirement, update=dict(project=project_output)
            )

    def list_requirements(self, project_id: int) -> list[Requirement]:
        return self._crud.read_all_from_db(Requirement, project_id=project_id)

    @router.get(
        "/catalog-modules/{catalog_module_id}/requirements",
        response_model=list[RequirementOutput],
        **kwargs
    )
    def _list_catalog_requirements(
        self, catalog_module_id: int
    ) -> Iterator[RequirementOutput]:
        catalog_module_output = self._catalog_modules._get_catalog_module(
            catalog_module_id
        )
        for requirement in self.list_catalog_requirements(catalog_module_id):
            yield RequirementOutput.from_orm(
                requirement, update=dict(catalog_module=catalog_module_output)
            )

    def list_catalog_requirements(self, catalog_module_id: int) -> list[Requirement]:
        query = select(Requirement).where(
            Requirement.catalog_module_id == catalog_module_id,
            Requirement.project_id == None,
        )
        return self._session.exec(query).all()

    @router.post(
        "/projects/{project_id}/requirements",
        status_code=201,
        response_model=RequirementOutput,
        **kwargs
    )
    def _create_requirement(
        self, project_id: int, requirement_input: RequirementInput
    ) -> RequirementOutput:
        # TODO: rename route to create_project_requirement
        return RequirementOutput.from_orm(
            self.create_requirement(project_id, requirement_input),
            update=dict(project=self._projects._get_project(project_id)),
        )

    def create_requirement(
        self, project_id: int, requirement_input: RequirementInput
    ) -> Requirement:
        requirement = Requirement.from_orm(requirement_input)
        requirement.project = self._projects.get_project(project_id)
        return self._crud.create_in_db(requirement)

    @router.post(
        "/catalog-modules/{catalog_module_id}/requirements",
        status_code=201,
        response_model=RequirementOutput,
        **kwargs
    )
    def _create_catalog_requirement(
        self, catalog_module_id: int, requirement_input: RequirementInput
    ) -> RequirementOutput:
        return RequirementOutput.from_orm(
            self.create_catalog_requirement(catalog_module_id, requirement_input),
            update=dict(
                catalog_module=self._catalog_modules._get_catalog_module(
                    catalog_module_id
                )
            ),
        )

    def create_catalog_requirement(
        self, catalog_module_id: int, requirement_input: RequirementInput
    ) -> Requirement:
        catalog_module = self._catalog_modules.get_catalog_module(catalog_module_id)
        requirement = Requirement.from_orm(requirement_input)
        requirement.catalog_module = catalog_module
        return self._crud.create_in_db(requirement)

    @router.post(
        "/projects/{project_id}/requirements/{requirement_id}",
        status_code=201,
        response_model=Requirement,
        **kwargs
    )
    def _copy_requirement_to_project(
        self, project_id: int, requirement_id: int
    ) -> RequirementOutput:
        requirement = self.copy_requirement_to_project(project_id, requirement_id)
        project_output = None
        catalog_module_output = None
        if requirement.project:
            project_output = self._projects._get_project(requirement.project.id)
        if requirement.catalog_module:
            catalog_module_output = self._catalog_modules._get_catalog_module(
                requirement.catalog_module.id
            )
        return RequirementOutput.from_orm(
            requirement,
            update=dict(project=project_output, catalog_module=catalog_module_output),
        )

    def copy_requirement_to_project(
        self, project_id: int, requirement_id: int
    ) -> Requirement:
        requirement_data = self.get_requirement(requirement_id).dict(
            exclude={"id", "created", "modified"}
        )
        requirement = Requirement(**requirement_data)
        requirement.project = self._projects.get_project(project_id)
        return self._crud.create_in_db(requirement)

    @router.post(
        "/catalog-modules/{catalog_module_id}/requirements/{requirement_id}",
        status_code=201,
        response_model=Requirement,
        **kwargs
    )
    def copy_requirement_to_catalog(
        self, catalog_module_id: int, requirement_id: int
    ) -> Requirement:
        # TODO: Implement route
        pass

    @router.get(
        "/requirements/{requirement_id}", response_model=RequirementOutput, **kwargs
    )
    def _get_requirement(self, requirement_id: int) -> RequirementOutput:
        requirement = self.get_requirement(requirement_id)
        return RequirementOutput.from_orm(
            requirement,
            update=dict(project=self._projects._get_project(requirement.project_id)),
        )

    def get_requirement(self, requirement_id: int) -> Requirement:
        return self._crud.read_from_db(Requirement, requirement_id)

    @router.put(
        "/requirements/{requirement_id}", response_model=RequirementOutput, **kwargs
    )
    def _update_requirement(
        self, requirement_id: int, requirement_input: RequirementInput
    ) -> RequirementOutput:
        requirement = self.update_requirement(requirement_id, requirement_input)
        return RequirementOutput.from_orm(
            requirement,
            update=dict(project=self._projects._get_project(requirement.project_id)),
        )

    def update_requirement(
        self, requirement_id: int, requirement_input: RequirementInput
    ) -> Requirement:
        requirement = self._crud.read_from_db(Requirement, requirement_id)
        updated_requirement = Requirement.from_orm(
            requirement_input,
            update=dict(
                project_id=requirement.project_id,
                gs_anforderung_reference=requirement.gs_anforderung_reference,
                gs_absicherung=requirement.gs_absicherung,
                gs_verantwortliche=requirement.gs_verantwortliche,
                catalog_module_id=requirement.catalog_module_id,
            ),
        )
        return self._crud.update_in_db(requirement_id, updated_requirement)

    @router.delete(
        "/requirements/{requirement_id}",
        status_code=204,
        response_class=Response,
        **kwargs
    )
    def delete_requirement(self, requirement_id: int) -> None:
        return self._crud.delete_from_db(Requirement, requirement_id)
