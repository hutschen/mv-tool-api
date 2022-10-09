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

from .catalogs import CatalogsView
from ..models import CatalogModule, CatalogModuleInput
from ..database import CRUDOperations

router = APIRouter()


@cbv(router)
class CatalogModulesView:
    kwargs = dict(tags=["catalog-module"])

    def __init__(
        self,
        catalogs: CatalogsView = Depends(CatalogsView),
        crud: CRUDOperations[CatalogModule] = Depends(CRUDOperations),
    ):
        self._catalogs = catalogs
        self._crud = crud

    @router.get(
        "/catalogs/{catalog_id}/catalog-modules",
        response_model=list[CatalogModule],
        **kwargs
    )
    def list_catalog_modules(self, catalog_id: int) -> list[CatalogModule]:
        return self._crud.read_all_from_db(CatalogModule, catalog_id=catalog_id)

    @router.post(
        "/catalogs/{catalog_id}/catalog-modules",
        status_code=201,
        response_model=CatalogModule,
        **kwargs
    )
    def create_catalog_module(
        self, catalog_id: int, catalog_module_input: CatalogModuleInput
    ) -> CatalogModule:
        catalog_module = CatalogModule.from_orm(catalog_module_input)
        catalog_module.catalog = self._catalogs.get_catalog(catalog_id)
        return self._crud.create_in_db(catalog_module)

    @router.get(
        "/catalog-modules/{catalog_module_id}", response_model=CatalogModule, **kwargs
    )
    def get_catalog_module(self, catalog_module_id: int) -> CatalogModule:
        return self._crud.read_from_db(CatalogModule, catalog_module_id)

    @router.put(
        "/catalog-modules/{catalog_module_id}", response_model=CatalogModule, **kwargs
    )
    def update_catalog_module(
        self, catalog_module_id: int, catalog_module_input: CatalogModuleInput
    ) -> CatalogModule:
        catalog_module = CatalogModule.from_orm(catalog_module_input)
        return self._crud.update_in_db(catalog_module_id, catalog_module)

    @router.delete("/catalog-modules/{catalog_module_id}", status_code=204, **kwargs)
    def delete_catalog_module(self, catalog_module_id: int) -> None:
        self._crud.delete_from_db(catalog_module_id)
