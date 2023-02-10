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

from typing import Any, Iterator
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from sqlmodel import or_

from mvtool.utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
)

from .catalogs import CatalogsView
from ..errors import NotFoundError
from ..models import (
    Catalog,
    CatalogModule,
    CatalogModuleInput,
    CatalogModuleOutput,
)
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
        self._session = self._crud.session

    @router.get(
        "/catalogs/{catalog_id}/catalog-modules",
        response_model=list[CatalogModuleOutput],
        **kwargs,
    )
    def _list_catalog_modules(self, catalog_id: int) -> Iterator[CatalogModuleOutput]:
        catalog_output = self._catalogs.get_catalog(catalog_id)
        for catalog_module in self.list_catalog_modules(catalog_id):
            yield CatalogModuleOutput.from_orm(
                catalog_module, update=dict(catalog=catalog_output)
            )

    def list_catalog_modules(self, catalog_id: int) -> list[CatalogModule]:
        return self._crud.read_all_from_db(CatalogModule, catalog_id=catalog_id)

    @router.post(
        "/catalogs/{catalog_id}/catalog-modules",
        status_code=201,
        response_model=CatalogModuleOutput,
        **kwargs,
    )
    def _create_catalog_module(
        self, catalog_id: int, catalog_module_input: CatalogModuleInput
    ) -> CatalogModuleOutput:
        return CatalogModuleOutput.from_orm(
            self.create_catalog_module(catalog_id, catalog_module_input),
            update=dict(catalog=self._catalogs.get_catalog(catalog_id)),
        )

    def create_catalog_module(
        self, catalog_id: int, catalog_module_input: CatalogModuleInput
    ) -> CatalogModule:
        catalog_module = CatalogModule.from_orm(catalog_module_input)
        catalog_module.catalog = self._catalogs.get_catalog(catalog_id)
        return self._crud.create_in_db(catalog_module)

    @router.get(
        "/catalog-modules/{catalog_module_id}",
        response_model=CatalogModuleOutput,
        **kwargs,
    )
    def _get_catalog_module(self, catalog_module_id: int) -> CatalogModuleOutput:
        catalog_module = self.get_catalog_module(catalog_module_id)
        return CatalogModuleOutput.from_orm(
            catalog_module,
            update=dict(catalog=self._catalogs.get_catalog(catalog_module.catalog_id)),
        )

    def get_catalog_module(self, catalog_module_id: int) -> CatalogModule:
        return self._crud.read_from_db(CatalogModule, catalog_module_id)

    @router.put(
        "/catalog-modules/{catalog_module_id}",
        response_model=CatalogModuleOutput,
        **kwargs,
    )
    def _update_catalog_module(
        self, catalog_module_id: int, catalog_module_input: CatalogModuleInput
    ) -> CatalogModuleOutput:
        catalog_module = self.update_catalog_module(
            catalog_module_id, catalog_module_input
        )
        return CatalogModuleOutput.from_orm(
            catalog_module,
            update=dict(catalog=self._catalogs.get_catalog(catalog_module.catalog_id)),
        )

    def update_catalog_module(
        self, catalog_module_id: int, catalog_module_input: CatalogModuleInput
    ) -> CatalogModule:
        catalog_module = self._session.get(CatalogModule, catalog_module_id)
        if not catalog_module:
            cls_name = CatalogModule.__name__
            raise NotFoundError(f"No {cls_name} with id={catalog_module_id}.")
        for key, value in catalog_module_input.dict().items():
            setattr(catalog_module, key, value)
        self._session.flush()
        return catalog_module

    @router.delete("/catalog-modules/{catalog_module_id}", status_code=204, **kwargs)
    def delete_catalog_module(self, catalog_module_id: int) -> None:
        self._crud.delete_from_db(CatalogModule, catalog_module_id)


def get_catalog_module_filters(
    # filter by pattern
    reference: str | None = None,
    title: str | None = None,
    description: str | None = None,
    #
    # filter by values
    references: list[str] | None = None,
    #
    # filter by ids
    catalog_ids: list[int] | None = None,
    #
    # filter for existence
    has_reference: bool | None = None,
    has_description: bool | None = None,
    #
    # filter by search string
    search: str | None = None,
) -> list[Any]:
    where_clauses = []

    # filter by pattern
    for column, value in [
        (CatalogModule.reference, reference),
        (CatalogModule.title, title),
        (CatalogModule.description, description),
    ]:
        if value is not None:
            where_clauses.append(filter_by_pattern(column, value))

    # filter by values
    for column, values in [
        (CatalogModule.reference, references),
        (CatalogModule.catalog_id, catalog_ids),
    ]:
        if values:
            where_clauses.append(filter_by_values(column, values))

    # filter for existence
    for column, value in [
        (CatalogModule.reference, has_reference),
        (CatalogModule.description, has_description),
    ]:
        if value is not None:
            where_clauses.append(filter_for_existence(column, value))

    # filter by search string
    if search:
        where_clauses.append(
            or_(
                filter_by_pattern(column, f"*{search}*")
                for column in (
                    CatalogModule.reference,
                    CatalogModule.title,
                    CatalogModule.description,
                    Catalog.reference,
                    Catalog.title,
                )
            )
        )

    return where_clauses
