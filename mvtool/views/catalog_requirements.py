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

from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv

from ..errors import NotFoundError
from ..database import CRUDOperations
from ..models import (
    CatalogRequirement,
    CatalogRequirementInput,
    CatalogRequirementOutput,
)
from .catalog_modules import CatalogModulesView

router = APIRouter()


@cbv(router)
class CatalogRequirementsView:
    kwargs = dict(tags=["catalog-requirement"])

    def __init__(
        self,
        catalog_modules: CatalogModulesView = Depends(CatalogModulesView),
        crud: CRUDOperations[CatalogRequirement] = Depends(CRUDOperations),
    ):
        self._catalog_modules = catalog_modules
        self._crud = crud
        self._session = self._crud.session

    @router.get(
        "/catalog-modules/{catalog_module_id}/catalog-requirements",
        response_model=list[CatalogRequirementOutput],
        **kwargs,
    )
    def list_catalog_requirements(
        self, catalog_module_id: int
    ) -> list[CatalogRequirement]:
        return self._crud.read_all_from_db(
            CatalogRequirement, catalog_module_id=catalog_module_id
        )

    @router.post(
        "/catalog-modules/{catalog_module_id}/catalog-requirements",
        response_model=CatalogRequirementOutput,
        status_code=201,
        **kwargs,
    )
    def create_catalog_requirement(
        self, catalog_module_id: int, catalog_requirement_input: CatalogRequirementInput
    ) -> CatalogRequirement:
        catalog_requirement = CatalogRequirement.from_orm(catalog_requirement_input)
        catalog_requirement.catalog_module = self._catalog_modules.get_catalog_module(
            catalog_module_id
        )
        return self._crud.create_in_db(catalog_requirement)

    @router.get(
        "/catalog-requirements/{catalog_requirement_id}",
        response_model=CatalogRequirementOutput,
        **kwargs,
    )
    def get_catalog_requirement(
        self, catalog_requirement_id: int
    ) -> CatalogRequirement:
        return self._crud.read_from_db(CatalogRequirement, catalog_requirement_id)

    @router.put(
        "/catalog-requirements/{catalog_requirement_id}",
        response_model=CatalogRequirementOutput,
        **kwargs,
    )
    def update_catalog_requirement(
        self,
        catalog_requirement_id: int,
        catalog_requirement_input: CatalogRequirementInput,
    ) -> CatalogRequirement:
        catalog_requirement = self._session.get(
            CatalogRequirement, catalog_requirement_id
        )
        if not catalog_requirement:
            cls_name = CatalogRequirement.__name__
            raise NotFoundError(f"No {cls_name} with id={catalog_requirement_id}.")
        for key, value in catalog_requirement_input.dict().items():
            setattr(catalog_requirement, key, value)
        self._session.flush()
        return catalog_requirement

    @router.delete(
        "/catalog-requirements/{catalog_requirement_id}",
        status_code=204,
        **kwargs,
    )
    def delete_catalog_requirement(self, catalog_requirement_id: int) -> None:
        return self._crud.delete_from_db(CatalogRequirement, catalog_requirement_id)
