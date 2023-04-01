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
from sqlmodel import Column, or_

from ..data.catalog_requirements import CatalogRequirementsView
from ..models.catalog_modules import CatalogModule
from ..models.catalog_requirements import (
    CatalogRequirement,
    CatalogRequirementInput,
    CatalogRequirementOutput,
    CatalogRequirementRepresentation,
)
from ..models.catalogs import Catalog
from ..utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
    search_columns,
)
from ..utils.pagination import Page, page_params
from .catalog_modules import CatalogModules


def get_catalog_requirement_filters(
    # filter by pattern
    reference: str | None = None,
    summary: str | None = None,
    description: str | None = None,
    gs_absicherung: str | None = None,
    gs_verantwortliche: str | None = None,
    #
    # filter by values
    references: list[str] | None = Query(None),
    gs_absicherungen: list[str] | None = Query(None),
    #
    # filter by ids
    ids: list[int] | None = Query(None),
    catalog_ids: list[int] | None = Query(None),
    catalog_module_ids: list[int] | None = Query(None),
    #
    # filter for existence
    has_reference: bool | None = None,
    has_description: bool | None = None,
    has_gs_absicherung: bool | None = None,
    has_gs_verantwortliche: bool | None = None,
    #
    # filter by search string
    search: str | None = None,
) -> list[Any]:
    where_clauses = []

    # filter by pattern
    for column, value in (
        (CatalogRequirement.reference, reference),
        (CatalogRequirement.summary, summary),
        (CatalogRequirement.description, description),
        (CatalogRequirement.gs_absicherung, gs_absicherung),
        (CatalogRequirement.gs_verantwortliche, gs_verantwortliche),
    ):
        if value:
            where_clauses.append(filter_by_pattern(column, value))

    # filter by values or ids
    for column, values in (
        (CatalogRequirement.reference, references),
        (CatalogRequirement.gs_absicherung, gs_absicherungen),
        (CatalogRequirement.id, ids),
        (CatalogModule.catalog_id, catalog_ids),
        (CatalogRequirement.catalog_module_id, catalog_module_ids),
    ):
        if values:
            where_clauses.append(filter_by_values(column, values))

    # filter for existence
    for column, value in (
        (CatalogRequirement.reference, has_reference),
        (CatalogRequirement.description, has_description),
        (CatalogRequirement.gs_absicherung, has_gs_absicherung),
        (CatalogRequirement.gs_verantwortliche, has_gs_verantwortliche),
    ):
        if value is not None:
            where_clauses.append(filter_for_existence(column, value))

    # filter by search string
    if search:
        where_clauses.append(
            or_(
                filter_by_pattern(column, f"*{search}*")
                for column in (
                    CatalogRequirement.reference,
                    CatalogRequirement.summary,
                    CatalogRequirement.description,
                    CatalogRequirement.gs_absicherung,
                    CatalogRequirement.gs_verantwortliche,
                    CatalogModule.reference,
                    CatalogModule.title,
                    Catalog.reference,
                    Catalog.title,
                )
            )
        )

    return where_clauses


def get_catalog_requirement_sort(
    sort_by: str | None = None, sort_order: constr(regex=r"^(asc|desc)$") | None = None
) -> list[Any]:
    if not (sort_by and sort_order):
        return []

    try:
        columns: list[Column] = {
            "reference": [CatalogRequirement.reference],
            "summary": [CatalogRequirement.summary],
            "description": [CatalogRequirement.description],
            "gs_absicherung": [CatalogRequirement.gs_absicherung],
            "gs_verantwortliche": [CatalogRequirement.gs_verantwortliche],
            "catalog": [Catalog.reference, Catalog.title],
            "catalog_module": [CatalogModule.reference, CatalogModule.title],
        }[sort_by]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by parameter: {sort_by}",
        )

    columns.append(CatalogRequirement.id)
    if sort_order == "asc":
        return [column.asc() for column in columns]
    else:
        return [column.desc() for column in columns]


router = APIRouter(tags=["catalog-requirement"])


@router.get(
    "/catalog-requirements",
    response_model=Page[CatalogRequirementOutput] | list[CatalogRequirementOutput],
)
def get_catalog_requirements(
    where_clauses=Depends(get_catalog_requirement_filters),
    order_by_clauses=Depends(get_catalog_requirement_sort),
    page_params=Depends(page_params),
    catalog_requirements_view: CatalogRequirementsView = Depends(),
) -> Page[CatalogRequirementOutput] | list[CatalogRequirement]:
    crequirements = catalog_requirements_view.list_catalog_requirements(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        crequirements_count = catalog_requirements_view.count_catalog_requirements(
            where_clauses
        )
        return Page[CatalogRequirementOutput](
            items=crequirements, total_count=crequirements_count
        )
    else:
        return crequirements


@router.post(
    "/catalog-modules/{catalog_module_id}/catalog-requirements",
    response_model=CatalogRequirementOutput,
    status_code=201,
)
def create_catalog_requirement(
    catalog_module_id: int,
    catalog_requirement_input: CatalogRequirementInput,
    catalog_modules_view: CatalogModules = Depends(),
    catalog_requirements_view: CatalogRequirementsView = Depends(),
) -> CatalogRequirement:
    catalog_module = catalog_modules_view.get_catalog_module(catalog_module_id)
    return catalog_requirements_view.create_catalog_requirement(
        catalog_module, catalog_requirement_input
    )


@router.get(
    "/catalog-requirements/{catalog_requirement_id}",
    response_model=CatalogRequirementOutput,
)
def get_catalog_requirement(
    catalog_requirement_id: int,
    catalog_requirements_view: CatalogRequirementsView = Depends(),
) -> CatalogRequirement:
    return catalog_requirements_view.get_catalog_requirement(catalog_requirement_id)


@router.put(
    "/catalog-requirements/{catalog_requirement_id}",
    response_model=CatalogRequirementOutput,
)
def update_catalog_requirement(
    catalog_requirement_id: int,
    catalog_requirement_input: CatalogRequirementInput,
    catalog_requirements_view: CatalogRequirementsView = Depends(),
) -> CatalogRequirement:
    catalog_requirement = catalog_requirements_view.get_catalog_requirement(
        catalog_requirement_id
    )
    catalog_requirements_view.update_catalog_requirement(
        catalog_requirement, catalog_requirement_input
    )
    return catalog_requirement


@router.delete("/catalog-requirements/{catalog_requirement_id}", status_code=204)
def delete_catalog_requirement(
    catalog_requirement_id: int,
    catalog_requirements_view: CatalogRequirementsView = Depends(),
) -> None:
    catalog_requirement = catalog_requirements_view.get_catalog_requirement(
        catalog_requirement_id
    )
    catalog_requirements_view.delete_catalog_requirement(catalog_requirement)


@router.get(
    "/catalog-requirement/representations",
    response_model=Page[CatalogRequirementRepresentation]
    | list[CatalogRequirementRepresentation],
)
def get_catalog_requirement_representations(
    where_clauses: list[Any] = Depends(get_catalog_requirement_filters),
    local_search: str | None = None,
    order_by_clauses=Depends(get_catalog_requirement_sort),
    page_params=Depends(page_params),
    catalog_requirements_view: CatalogRequirementsView = Depends(),
) -> Page[CatalogRequirementRepresentation] | list[CatalogRequirement]:
    if local_search:
        where_clauses.append(
            search_columns(
                local_search, CatalogRequirement.reference, CatalogRequirement.summary
            )
        )

    crequirements = catalog_requirements_view.list_catalog_requirements(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        crequirements_count = catalog_requirements_view.count_catalog_requirements(
            where_clauses
        )
        return Page[CatalogRequirementRepresentation](
            items=crequirements, total_count=crequirements_count
        )
    else:
        return crequirements


@router.get("/catalog-requirement/field-names", response_model=list[str])
def get_catalog_requirement_field_names(
    where_clauses=Depends(get_catalog_requirement_filters),
    catalog_requirements_view: CatalogRequirementsView = Depends(),
) -> set[str]:
    field_names = {"id", "summary", "catalog_module"}
    for field, names in [
        (CatalogRequirement.reference, ["reference"]),
        (CatalogRequirement.description, ["description"]),
        (CatalogRequirement.gs_absicherung, ["gs_absicherung"]),
        (CatalogRequirement.gs_verantwortliche, ["gs_verantwortliche"]),
    ]:
        if catalog_requirements_view.count_catalog_requirements(
            [filter_for_existence(field, True), *where_clauses]
        ):
            field_names.update(names)
    return field_names


@router.get("/catalog-requirement/references", response_model=Page[str] | list[str])
def get_catalog_requirement_references(
    where_clauses: list[Any] = Depends(get_catalog_requirement_filters),
    local_search: str | None = None,
    page_params=Depends(page_params),
    catalog_requirements_view: CatalogRequirementsView = Depends(),
) -> Page[str] | list[str]:
    if local_search:
        where_clauses.append(search_columns(local_search, CatalogRequirement.reference))
    references = catalog_requirements_view.list_catalog_requirement_values(
        CatalogRequirement.reference, where_clauses, **page_params
    )
    if page_params:
        references_count = catalog_requirements_view.count_catalog_requirement_values(
            CatalogRequirement.reference, where_clauses
        )
        return Page[str](items=references, total_count=references_count)
    else:
        return references
