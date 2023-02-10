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

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_utils.cbv import cbv
from pydantic import constr
from sqlmodel import Column, func, or_, select
from sqlmodel.sql.expression import Select

from ..utils.pagination import Page, page_params
from ..utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
)
from ..errors import NotFoundError
from ..auth import get_jira
from ..models import Catalog, CatalogInput, CatalogOutput, CatalogRepresentation
from ..database import CRUDOperations

router = APIRouter()


@cbv(router)
class CatalogsView:
    kwargs = dict(tags=["catalog"])

    def __init__(
        self,
        crud: CRUDOperations[Catalog] = Depends(CRUDOperations),
        _=Depends(get_jira),  # get jira to enforce login
    ):
        self._crud = crud
        self._session = self._crud.session

    @staticmethod
    def _modify_catalogs_query(
        query: Select,
        where_clauses: list[Any] | None = None,
        order_by_clauses: list[Any] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Select:
        """Modify a query to include all required clauses and offset and limit."""
        if where_clauses:
            query = query.where(*where_clauses)
        if order_by_clauses:
            query = query.order_by(*order_by_clauses)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query

    def list_catalogs(
        self,
        where_clauses: list[Any] | None = None,
        order_by_clauses: list[Any] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Catalog]:
        query = self._modify_catalogs_query(
            select(Catalog),
            where_clauses,
            order_by_clauses or [Catalog.id],
            offset,
            limit,
        )
        return self._session.exec(query).all()

    def count_catalogs(self, where_clauses: list[Any] | None = None) -> int:
        query = self._modify_catalogs_query(
            select([func.count()]).select_from(Catalog), where_clauses
        )
        return self._session.execute(query).scalar()

    def list_catalog_values(
        self,
        column: Column,
        where_clauses: list[Any] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        query = self._modify_catalogs_query(
            select([func.distinct(column)]).select_from(Catalog),
            [filter_for_existence(column), *where_clauses],
            offset=offset,
            limit=limit,
        )
        return self._session.exec(query).all()

    def count_catalog_values(
        self, column: Column, where_clauses: list[Any] | None = None
    ) -> int:
        query = self._modify_catalogs_query(
            select([func.count(func.distinct(column))]).select_from(Catalog),
            [filter_for_existence(column), *where_clauses],
        )
        return self._session.execute(query).scalar()

    @router.post("/catalogs", status_code=201, response_model=CatalogOutput, **kwargs)
    def create_catalog(self, catalog_input: CatalogInput) -> Catalog:
        catalog = Catalog.from_orm(catalog_input)
        return self._crud.create_in_db(catalog)

    @router.get("/catalogs/{catalog_id}", response_model=CatalogOutput, **kwargs)
    def get_catalog(self, catalog_id: int) -> Catalog:
        return self._crud.read_from_db(Catalog, catalog_id)

    @router.put("/catalogs/{catalog_id}", response_model=CatalogOutput, **kwargs)
    def update_catalog(self, catalog_id: int, catalog_input: CatalogInput) -> Catalog:
        catalog = self._session.get(Catalog, catalog_id)
        if not catalog:
            cls_name = Catalog.__name__
            raise NotFoundError(f"No {cls_name} with id={catalog_id}.")
        for key, value in catalog_input.dict().items():
            setattr(catalog, key, value)
        self._session.flush()
        return catalog

    @router.delete("/catalogs/{catalog_id}", status_code=204, **kwargs)
    def delete_catalog(self, catalog_id: int) -> None:
        return self._crud.delete_from_db(Catalog, catalog_id)


def get_catalog_filters(
    # filter by pattern
    reference: str | None = None,
    title: str | None = None,
    description: str | None = None,
    #
    # filter by values
    references: list[str] | None = Query(None),
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
        (Catalog.reference, reference),
        (Catalog.title, title),
        (Catalog.description, description),
    ]:
        if value is not None:
            where_clauses.append(filter_by_pattern(column, value))

    # filter by values
    if references:
        where_clauses.append(filter_by_values(Catalog.reference, references))

    # filter for existence
    for column, value in [
        (Catalog.reference, has_reference),
        (Catalog.description, has_description),
    ]:
        if value is not None:
            where_clauses.append(filter_for_existence(column, value))

    # filter by search string
    if search:
        where_clauses.append(
            or_(
                filter_by_pattern(column, f"*{search}*")
                for column in (Catalog.reference, Catalog.title, Catalog.description)
            )
        )

    return where_clauses


def get_catalog_sort(
    sort_by: str | None = None, sort_order: constr(regex=r"^(asc|desc)$") | None = None
) -> list[Any]:
    if not (sort_by and sort_order):
        return []

    try:
        columns: list[Column] = {
            "reference": [Catalog.reference],
            "title": [Catalog.title],
            "description": [Catalog.description],
        }[sort_by]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by parameter: {sort_by}",
        )

    columns.append(Catalog.id)
    if sort_order == "asc":
        return [column.asc() for column in columns]
    else:
        return [column.desc() for column in columns]


@router.get(
    "/catalogs",
    response_model=Page[CatalogOutput] | list[CatalogOutput],
    **CatalogsView.kwargs,
)
def get_catalogs(
    where_clauses=Depends(get_catalog_filters),
    order_by_clauses=Depends(get_catalog_sort),
    page_params=Depends(page_params),
    catalogs_view: CatalogsView = Depends(),
):
    catalogs = catalogs_view.list_catalogs(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        catalogs_count = catalogs_view.count_catalogs(where_clauses)
        return Page[CatalogOutput](items=catalogs, total_count=catalogs_count)
    else:
        return catalogs


@router.get(
    "/catalog/representations",
    response_model=Page[CatalogRepresentation] | list[CatalogRepresentation],
    **CatalogsView.kwargs,
)
def get_catalog_representations(
    where_clauses=Depends(get_catalog_filters),
    order_by_clauses=Depends(get_catalog_sort),
    page_params=Depends(page_params),
    catalogs_view: CatalogsView = Depends(),
):
    catalogs = catalogs_view.list_catalogs(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        catalogs_count = catalogs_view.count_catalogs(where_clauses)
        return Page[CatalogRepresentation](items=catalogs, total_count=catalogs_count)
    else:
        return catalogs


@router.get(
    "/catalog/field-names",
    response_model=list[str],
    **CatalogsView.kwargs,
)
def get_catalog_field_names(
    where_clauses=Depends(get_catalog_filters),
    catalogs_view: CatalogsView = Depends(),
) -> set[str]:
    field_names = {"id", "title"}
    for field, names in [
        (Catalog.reference, ["reference"]),
        (Catalog.description, ["description"]),
    ]:
        if catalogs_view.count_catalogs(
            [filter_for_existence(field, True), *where_clauses]
        ):
            field_names.update(names)
    return field_names


@router.get(
    "/catalog/references",
    response_model=Page[str] | list[str],
    **CatalogsView.kwargs,
)
def get_catalog_references(
    where_clauses=Depends(get_catalog_filters),
    local_search: str | None = None,
    page_params=Depends(page_params),
    catalogs_view: CatalogsView = Depends(),
):
    if local_search:
        where_clauses.append(filter_by_pattern(Catalog.reference, f"*{local_search}*"))

    references = catalogs_view.list_catalog_values(
        Catalog.reference, where_clauses, **page_params
    )
    if page_params:
        references_count = catalogs_view.count_catalog_values(
            Catalog.reference, where_clauses
        )
        return Page[str](items=references, total_count=references_count)
    else:
        return references
