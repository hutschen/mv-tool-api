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

from typing import Any, Iterable, Iterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_utils.cbv import cbv
from pydantic import constr
from sqlmodel import Column, func, or_, select
from sqlmodel.sql.expression import Select
from mvtool.utils.etag_map import get_from_etag_map

from mvtool.utils.iteration import CachedIterable

from ..database import CRUDOperations, read_from_db
from ..models.catalog_modules import (
    CatalogModule,
    CatalogModuleImport,
    CatalogModuleInput,
    CatalogModuleOutput,
    CatalogModuleRepresentation,
)
from ..models.catalogs import Catalog
from ..utils.errors import NotFoundError
from ..utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
    search_columns,
)
from ..utils.pagination import Page, page_params
from .catalogs import CatalogsView

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

    @staticmethod
    def _modify_catalog_modules_query(
        query: Select,
        where_clauses: list[Any] | None = None,
        order_by_clauses: list[Any] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Select:
        """Modify a query to include all required clauses and offset and limit."""
        query = query.join(Catalog)
        if where_clauses:
            query = query.where(*where_clauses)
        if order_by_clauses:
            query = query.order_by(*order_by_clauses)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query

    def list_catalog_modules(
        self,
        where_clauses: Any = None,
        order_by_clauses: Any = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[CatalogModule]:
        query = self._modify_catalog_modules_query(
            select(CatalogModule),
            where_clauses,
            order_by_clauses or [CatalogModule.id],
            offset,
            limit,
        )
        return self._session.exec(query).all()

    def count_catalog_modules(self, where_clauses: Any = None) -> int:
        query = self._modify_catalog_modules_query(
            select([func.count()]).select_from(CatalogModule),
            where_clauses,
        )
        return self._session.execute(query).scalar()

    def list_catalog_module_values(
        self,
        column: Column,
        where_clauses: list[Any] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        query = self._modify_catalog_modules_query(
            select([func.distinct(column)]).select_from(CatalogModule),
            [filter_for_existence(column), *where_clauses],
            offset=offset,
            limit=limit,
        )
        return self._session.exec(query).all()

    def count_catalog_module_values(
        self, column: Column, where_clauses: list[Any] | None = None
    ) -> int:
        query = self._modify_catalog_modules_query(
            select([func.count(func.distinct(column))]).select_from(CatalogModule),
            [filter_for_existence(column), *where_clauses],
        )
        return self._session.execute(query).scalar()

    def create_catalog_module(
        self,
        catalog: Catalog,
        creation: CatalogModuleInput | CatalogModuleImport,
        skip_flush: bool = False,
    ) -> CatalogModule:
        catalog_module = CatalogModule(**creation.dict(exclude={"id", "catalog"}))
        catalog_module.catalog = catalog
        self._session.add(catalog_module)
        if not skip_flush:
            self._session.flush()
        return catalog_module

    def get_catalog_module(self, catalog_module_id: int) -> CatalogModule:
        return read_from_db(self._session, CatalogModule, catalog_module_id)

    def update_catalog_module(
        self,
        catalog_module: CatalogModule,
        update: CatalogModuleInput | CatalogModuleImport,
        patch: bool = False,
        skip_flush: bool = False,
    ) -> None:
        for key, value in update.dict(
            exclude_unset=patch, exclude={"id", "catalog"}
        ).items():
            setattr(catalog_module, key, value)

        if not skip_flush:
            self._session.flush()

    @router.delete("/catalog-modules/{catalog_module_id}", status_code=204, **kwargs)
    def delete_catalog_module(self, catalog_module_id: int) -> None:
        self._crud.delete_from_db(CatalogModule, catalog_module_id)

    def bulk_create_update_catalog_modules(
        self,
        fallback_catalog: Catalog,
        catalog_module_imports: Iterable[CatalogModuleImport],
        patch: bool = False,
        skip_flush: bool = False,
    ) -> Iterator[CatalogModule]:
        catalog_module_imports = CachedIterable(catalog_module_imports)

        # Convert catalog imports to catalogs
        catalogs_map = self._catalogs.convert_catalog_imports(
            (c.catalog for c in catalog_module_imports if c.catalog is not None),
            patch=patch,
        )

        # Get catalog modules to be updated from database
        ids = [c.id for c in catalog_module_imports if c.id is not None]
        catalog_modules_to_update = {
            c.id: c
            for c in (
                self.list_catalog_modules([CatalogModule.id.in_(ids)]) if ids else []
            )
        }

        # Create or update catalog modules
        for catalog_module_import in catalog_module_imports:
            catalog = get_from_etag_map(catalogs_map, catalog_module_import.catalog)

            if catalog_module_import.id is None:
                # Create new catalog module
                yield self.create_catalog_module(
                    catalog or fallback_catalog, catalog_module_import, skip_flush=True
                )
            else:
                # Update existing catalog module
                catalog_module = catalog_modules_to_update.get(catalog_module_import.id)
                if catalog_module is None:
                    raise NotFoundError(
                        f"No catalog module with id={catalog_module_import.id}."
                    )
                self.update_catalog_module(
                    catalog_module, catalog_module_import, patch=patch, skip_flush=True
                )
                if catalog:
                    catalog_module.catalog = catalog
                yield catalog_module

        if not skip_flush:
            self._session.flush()


def get_catalog_module_filters(
    # filter by pattern
    reference: str | None = None,
    title: str | None = None,
    description: str | None = None,
    #
    # filter by values
    references: list[str] | None = Query(None),
    #
    # filter by ids
    ids: list[int] | None = Query(None),
    catalog_ids: list[int] | None = Query(None),
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

    # filter by values or ids
    for column, values in [
        (CatalogModule.reference, references),
        (CatalogModule.id, ids),
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


def get_catalog_module_sort(
    sort_by: str | None = None, sort_order: constr(regex=r"^(asc|desc)$") | None = None
) -> list[Any]:
    if not (sort_by and sort_order):
        return []

    try:
        columns: list[Column] = {
            "reference": [CatalogModule.reference],
            "title": [CatalogModule.title],
            "description": [CatalogModule.description],
            "catalog": [Catalog.reference, Catalog.title],
        }[sort_by]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by parameter: {sort_by}",
        )

    columns.append(CatalogModule.id)
    if sort_order == "asc":
        return [column.asc() for column in columns]
    else:
        return [column.desc() for column in columns]


@router.get(
    "/catalog-modules",
    response_model=Page[CatalogModuleOutput] | list[CatalogModuleOutput],
    **CatalogModulesView.kwargs,
)
def get_catalog_modules(
    where_clauses=Depends(get_catalog_module_filters),
    order_by_clauses=Depends(get_catalog_module_sort),
    page_params=Depends(page_params),
    catalog_modules_view: CatalogModulesView = Depends(),
):
    cmodules = catalog_modules_view.list_catalog_modules(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        cmodule_count = catalog_modules_view.count_catalog_modules(where_clauses)
        return Page[CatalogModuleOutput](items=cmodules, total_count=cmodule_count)
    else:
        return cmodules


@router.post(
    "/catalogs/{catalog_id}/catalog-modules",
    status_code=201,
    response_model=CatalogModuleOutput,
    **CatalogModulesView.kwargs,
)
def create_catalog_module(
    catalog_id: int,
    catalog_module_input: CatalogModuleInput,
    catalogs_view: CatalogsView = Depends(),
    catalog_modules_view: CatalogModulesView = Depends(),
) -> CatalogModule:
    catalog = catalogs_view.get_catalog(catalog_id)
    return catalog_modules_view.create_catalog_module(catalog, catalog_module_input)


@router.get(
    "/catalog-modules/{catalog_module_id}",
    response_model=CatalogModuleOutput,
    **CatalogModulesView.kwargs,
)
def get_catalog_module(
    catalog_module_id: int, catalog_modules_view: CatalogModulesView = Depends()
) -> CatalogModule:
    return catalog_modules_view.get_catalog_module(catalog_module_id)


@router.put(
    "/catalog-modules/{catalog_module_id}",
    response_model=CatalogModuleOutput,
    **CatalogModulesView.kwargs,
)
def update_catalog_module(
    catalog_module_id: int,
    catalog_module_input: CatalogModuleInput,
    catalog_modules_view: CatalogModulesView = Depends(),
) -> CatalogModule:
    catalog_module = catalog_modules_view.get_catalog_module(catalog_module_id)
    catalog_modules_view.update_catalog_module(catalog_module, catalog_module_input)
    return catalog_module


@router.get(
    "/catalog-module/representations",
    response_model=Page[CatalogModuleRepresentation]
    | list[CatalogModuleRepresentation],
    **CatalogModulesView.kwargs,
)
def get_catalog_module_representation(
    where_clauses: list[Any] = Depends(get_catalog_module_filters),
    local_search: str | None = None,
    order_by_clauses=Depends(get_catalog_module_sort),
    page_params=Depends(page_params),
    catalog_modules_view: CatalogModulesView = Depends(),
):
    if local_search:
        where_clauses.append(
            search_columns(local_search, CatalogModule.reference, CatalogModule.title)
        )

    cmodules = catalog_modules_view.list_catalog_modules(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        cmodule_count = catalog_modules_view.count_catalog_modules(where_clauses)
        return Page[CatalogModuleRepresentation](
            items=cmodules, total_count=cmodule_count
        )
    else:
        return cmodules


@router.get(
    "/catalog-module/field-names",
    response_model=list[str],
    **CatalogModulesView.kwargs,
)
def get_catalog_module_field_names(
    where_clauses=Depends(get_catalog_module_filters),
    catalog_modules_view: CatalogModulesView = Depends(),
) -> set[str]:
    field_names = {"id", "title", "catalog"}
    for field, names in [
        (CatalogModule.reference, ["reference"]),
        (CatalogModule.description, ["description"]),
    ]:
        if catalog_modules_view.count_catalog_modules(
            [filter_for_existence(field, True), *where_clauses]
        ):
            field_names.update(names)
    return field_names


@router.get(
    "/catalog-module/references",
    response_model=Page[str] | list[str],
    **CatalogModulesView.kwargs,
)
def get_catalog_module_references(
    where_clauses=Depends(get_catalog_module_filters),
    local_search: str | None = None,
    page_params=Depends(page_params),
    catalog_modules_view: CatalogModulesView = Depends(),
):
    if local_search:
        where_clauses.append(search_columns(local_search, CatalogModule.reference))

    references = catalog_modules_view.list_catalog_module_values(
        CatalogModule.reference, where_clauses, **page_params
    )
    if page_params:
        reference_count = catalog_modules_view.count_catalog_module_values(
            CatalogModule.reference, where_clauses
        )
        return Page[str](items=references, total_count=reference_count)
    else:
        return references
