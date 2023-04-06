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

import shutil
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from pydantic import constr
from sqlmodel import Column, Session, or_

from ..data.catalog_modules import CatalogModules
from ..database import get_session
from ..gs_parser import GSBausteinParser
from ..models.catalog_modules import (
    CatalogModule,
    CatalogModuleInput,
    CatalogModuleOutput,
    CatalogModuleRepresentation,
)
from ..models.catalogs import Catalog
from ..utils.errors import ValueHttpError
from ..utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
    search_columns,
)
from ..utils.pagination import Page, page_params
from ..utils.temp_file import get_temp_file
from .catalogs import Catalogs


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


router = APIRouter(tags=["catalog-module"])


@router.get(
    "/catalog-modules",
    response_model=Page[CatalogModuleOutput] | list[CatalogModuleOutput],
)
def get_catalog_modules(
    where_clauses=Depends(get_catalog_module_filters),
    order_by_clauses=Depends(get_catalog_module_sort),
    page_params=Depends(page_params),
    catalog_modules_view: CatalogModules = Depends(),
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
)
def create_catalog_module(
    catalog_id: int,
    catalog_module_input: CatalogModuleInput,
    catalogs_view: Catalogs = Depends(),
    catalog_modules_view: CatalogModules = Depends(),
) -> CatalogModule:
    catalog = catalogs_view.get_catalog(catalog_id)
    return catalog_modules_view.create_catalog_module(catalog, catalog_module_input)


@router.get("/catalog-modules/{catalog_module_id}", response_model=CatalogModuleOutput)
def get_catalog_module(
    catalog_module_id: int, catalog_modules_view: CatalogModules = Depends()
) -> CatalogModule:
    return catalog_modules_view.get_catalog_module(catalog_module_id)


@router.put("/catalog-modules/{catalog_module_id}", response_model=CatalogModuleOutput)
def update_catalog_module(
    catalog_module_id: int,
    catalog_module_input: CatalogModuleInput,
    catalog_modules_view: CatalogModules = Depends(),
) -> CatalogModule:
    catalog_module = catalog_modules_view.get_catalog_module(catalog_module_id)
    catalog_modules_view.update_catalog_module(catalog_module, catalog_module_input)
    return catalog_module


@router.delete("/catalog-modules/{catalog_module_id}", status_code=204)
def delete_catalog_module(
    catalog_module_id: int, catalog_modules_view: CatalogModules = Depends()
) -> None:
    catalog_module = catalog_modules_view.get_catalog_module(catalog_module_id)
    catalog_modules_view.delete_catalog_module(catalog_module)


@router.get(
    "/catalog-module/representations",
    response_model=Page[CatalogModuleRepresentation]
    | list[CatalogModuleRepresentation],
)
def get_catalog_module_representation(
    where_clauses: list[Any] = Depends(get_catalog_module_filters),
    local_search: str | None = None,
    order_by_clauses=Depends(get_catalog_module_sort),
    page_params=Depends(page_params),
    catalog_modules_view: CatalogModules = Depends(),
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
)
def get_catalog_module_field_names(
    where_clauses=Depends(get_catalog_module_filters),
    catalog_modules_view: CatalogModules = Depends(),
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
)
def get_catalog_module_references(
    where_clauses=Depends(get_catalog_module_filters),
    local_search: str | None = None,
    page_params=Depends(page_params),
    catalog_modules_view: CatalogModules = Depends(),
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


@router.post(
    "/catalogs/{catalog_id}/catalog-modules/gs-baustein",
    status_code=201,
    response_model=CatalogModule,
)
def upload_gs_baustein(
    catalog_id: int,
    upload_file: UploadFile,
    temp_file: NamedTemporaryFile = Depends(get_temp_file(".docx")),
    catalogs: Catalogs = Depends(),
    session: Session = Depends(get_session),
) -> CatalogModule:
    catalog = catalogs.get_catalog(catalog_id)
    shutil.copyfileobj(upload_file.file, temp_file.file)

    # Parse GS Baustein and save it and its requirements in the database
    catalog_module = GSBausteinParser.parse(temp_file.name)
    if catalog_module is None:
        raise ValueHttpError("Could not parse GS Baustein")

    # Assign catalog and save catalog module to database
    catalog_module.catalog = catalog
    session.add(catalog_module)
    session.flush()
    return catalog_module
