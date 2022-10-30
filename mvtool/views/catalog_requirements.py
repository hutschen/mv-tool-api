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

from ..database import CRUDOperations
from ..models import CatalogRequirement
from .catalog_modules import CatalogModulesView

router = APIRouter()


@cbv(router)
class CatalogRequirementsView:
    kwargs = dict(tags=["catalog_requirement"])

    def __init__(
        self,
        catalog_modules: CatalogModulesView = Depends(CatalogModulesView),
        crud: CRUDOperations[CatalogRequirement] = Depends(CRUDOperations),
    ):
        self._catalog_modules = catalog_modules
        self._crud = crud
        self._session = self._crud.session

    def list_catalog_requirements(self, catalog_module_id: int):
        pass

    def create_catalog_requirement(
        self, catalog_module_id: int, catalog_requirement: CatalogRequirement
    ):
        pass

    def get_catalog_requirement(self, catalog_requirement_id: int):
        pass

    def update_catalog_requirement(
        self, catalog_requirement_id: int, catalog_requirement: CatalogRequirement
    ):
        pass

    def delete_catalog_requirement(self, catalog_requirement_id: int):
        pass
