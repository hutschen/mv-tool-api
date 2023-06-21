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
from pydantic import constr
from sqlalchemy import Column

from ..db.schema import Catalog

from ..data.catalogs import Catalogs
from ..models.catalogs import (
    CatalogInput,
    CatalogOutput,
    CatalogRepresentation,
)
from ..utils.filtering import (
    filter_by_pattern_many,
    filter_by_values_many,
    filter_for_existence,
    filter_for_existence_many,
    search_columns,
)
from ..utils.pagination import Page, page_params


def get_catalog_filters(
    # filter by pattern
    reference: str | None = None,
    title: str | None = None,
    description: str | None = None,
    neg_reference: bool = False,
    neg_title: bool = False,
    neg_description: bool = False,
    #
    # filter by values
    references: list[str] | None = Query(None),
    neg_references: bool = False,
    #
    # filter by ids
    ids: list[int] | None = Query(None),
    neg_ids: bool = False,
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
    where_clauses.extend(
        filter_by_pattern_many(
            (Catalog.reference, reference, neg_reference),
            (Catalog.title, title, neg_title),
            (Catalog.description, description, neg_description),
        )
    )

    # filter by values or by ids
    where_clauses.extend(
        filter_by_values_many(
            (Catalog.id, ids, neg_ids),
            (Catalog.reference, references, neg_references),
        )
    )

    # filter for existence
    where_clauses.extend(
        filter_for_existence_many(
            (Catalog.reference, has_reference),
            (Catalog.description, has_description),
        )
    )

    # filter by search string
    if search:
        where_clauses.append(
            search_columns(
                search, Catalog.reference, Catalog.title, Catalog.description
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


router = APIRouter(tags=["catalog"])


@router.get("/catalogs", response_model=Page[CatalogOutput] | list[CatalogOutput])
def get_catalogs(
    where_clauses=Depends(get_catalog_filters),
    order_by_clauses=Depends(get_catalog_sort),
    page_params=Depends(page_params),
    catalogs: Catalogs = Depends(),
):
    catalogs_list = catalogs.list_catalogs(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        return Page[CatalogOutput](
            items=catalogs_list, total_count=catalogs.count_catalogs(where_clauses)
        )
    else:
        return catalogs_list


@router.post("/catalogs", status_code=201, response_model=CatalogOutput)
def create_catalog(
    catalog: CatalogInput,
    catalogs: Catalogs = Depends(),
) -> Catalog:
    return catalogs.create_catalog(catalog)


@router.get("/catalogs/{catalog_id}", response_model=CatalogOutput)
def get_catalog(catalog_id: int, catalogs: Catalogs = Depends()) -> Catalog:
    return catalogs.get_catalog(catalog_id)


@router.put("/catalogs/{catalog_id}", response_model=CatalogOutput)
def update_catalog(
    catalog_id: int,
    catalog_input: CatalogInput,
    catalogs: Catalogs = Depends(),
) -> Catalog:
    catalog = catalogs.get_catalog(catalog_id)
    catalogs.update_catalog(catalog, catalog_input)
    return catalog


@router.delete("/catalogs/{catalog_id}", status_code=204)
def delete_catalog(
    catalog_id: int,
    catalogs: Catalogs = Depends(),
) -> None:
    catalogs.delete_catalog(catalogs.get_catalog(catalog_id))


@router.delete("/catalogs", status_code=204)
def delete_catalogs(
    where_clauses=Depends(get_catalog_filters),
    catalogs: Catalogs = Depends(),
) -> None:
    catalogs_ = catalogs.list_catalogs(where_clauses)
    for catalog in catalogs_:
        catalogs.delete_catalog(catalog, skip_flush=True)
    catalogs._session.flush()


@router.get(
    "/catalog/representations",
    response_model=Page[CatalogRepresentation] | list[CatalogRepresentation],
)
def get_catalog_representations(
    where_clauses=Depends(get_catalog_filters),
    local_search: str | None = None,
    order_by_clauses=Depends(get_catalog_sort),
    page_params=Depends(page_params),
    catalogs: Catalogs = Depends(),
):
    if local_search:
        where_clauses.append(
            search_columns(local_search, Catalog.reference, Catalog.title)
        )

    catalogs_list = catalogs.list_catalogs(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        return Page[CatalogRepresentation](
            items=catalogs_list,
            total_count=catalogs.count_catalogs(where_clauses),
        )
    else:
        return catalogs_list


@router.get("/catalog/field-names", response_model=list[str])
def get_catalog_field_names(
    where_clauses=Depends(get_catalog_filters),
    catalogs: Catalogs = Depends(),
) -> set[str]:
    field_names = {"id", "title"}
    for field, names in [
        (Catalog.reference, ["reference"]),
        (Catalog.description, ["description"]),
    ]:
        if catalogs.count_catalogs([filter_for_existence(field, True), *where_clauses]):
            field_names.update(names)
    return field_names


@router.get("/catalog/references", response_model=Page[str] | list[str])
def get_catalog_references(
    where_clauses: list[Any] = Depends(get_catalog_filters),
    local_search: str | None = None,
    page_params=Depends(page_params),
    catalogs: Catalogs = Depends(),
):
    if local_search:
        where_clauses.append(search_columns(local_search, Catalog.reference))

    references = catalogs.list_catalog_values(
        Catalog.reference, where_clauses, **page_params
    )
    if page_params:
        return Page[str](
            items=references,
            total_count=catalogs.count_catalog_values(Catalog.reference, where_clauses),
        )
    else:
        return references
