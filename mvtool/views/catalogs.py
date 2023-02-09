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
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_utils.cbv import cbv
from pydantic import constr
from sqlmodel import Column, or_

from ..utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
)
from ..errors import NotFoundError
from ..auth import get_jira
from ..models import Catalog, CatalogInput, CatalogOutput
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

    @router.get("/catalogs", response_model=list[CatalogOutput], **kwargs)
    def _list_catalogs(self) -> Iterator[CatalogOutput]:
        for catalog in self.list_catalogs():
            yield CatalogOutput.from_orm(catalog)

    def list_catalogs(self) -> list[Catalog]:
        return self._crud.read_all_from_db(Catalog)

    @router.post("/catalogs", status_code=201, response_model=CatalogOutput, **kwargs)
    def _create_catalog(self, catalog_input: CatalogInput) -> CatalogOutput:
        catalog = self.create_catalog(catalog_input)
        return CatalogOutput.from_orm(catalog)

    def create_catalog(self, catalog_input: CatalogInput) -> Catalog:
        catalog = Catalog.from_orm(catalog_input)
        return self._crud.create_in_db(catalog)

    @router.get("/catalogs/{catalog_id}", response_model=CatalogOutput, **kwargs)
    def _get_catalog(self, catalog_id: int) -> CatalogOutput:
        catalog = self.get_catalog(catalog_id)
        return CatalogOutput.from_orm(catalog)

    def get_catalog(self, catalog_id: int) -> Catalog:
        return self._crud.read_from_db(Catalog, catalog_id)

    @router.put("/catalogs/{catalog_id}", response_model=CatalogOutput, **kwargs)
    def _update_catalog(
        self, catalog_id: int, catalog_input: CatalogInput
    ) -> CatalogOutput:
        catalog = self.update_catalog(catalog_id, catalog_input)
        return CatalogOutput.from_orm(catalog)

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
