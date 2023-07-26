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

from ..data.catalog_requirements import CatalogRequirements
from ..db.schema import Catalog, CatalogModule, CatalogRequirement
from ..models.catalog_requirements import (
    CatalogRequirementInput,
    CatalogRequirementOutput,
    CatalogRequirementPatch,
    CatalogRequirementRepresentation,
)
from ..utils.filtering import (
    filter_by_pattern_many,
    filter_by_values_many,
    filter_for_existence,
    filter_for_existence_many,
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
    neg_reference: bool = False,
    neg_summary: bool = False,
    neg_description: bool = False,
    neg_gs_absicherung: bool = False,
    neg_gs_verantwortliche: bool = False,
    #
    # filter by values
    references: list[str] | None = Query(None),
    gs_absicherungen: list[str] | None = Query(None),
    neg_references: bool = False,
    neg_gs_absicherungen: bool = False,
    #
    # filter by ids
    ids: list[int] | None = Query(None),
    catalog_ids: list[int] | None = Query(None),
    catalog_module_ids: list[int] | None = Query(None),
    neg_ids: bool = False,
    neg_catalog_ids: bool = False,
    neg_catalog_module_ids: bool = False,
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
    where_clauses.extend(
        filter_by_pattern_many(
            # fmt: off
            (CatalogRequirement.reference, reference, neg_reference),
            (CatalogRequirement.summary, summary, neg_summary),
            (CatalogRequirement.description, description, neg_description),
            (CatalogRequirement.gs_absicherung, gs_absicherung, neg_gs_absicherung),
            (CatalogRequirement.gs_verantwortliche, gs_verantwortliche, neg_gs_verantwortliche),
            # fmt: on
        )
    )

    # filter by values or ids
    where_clauses.extend(
        filter_by_values_many(
            # fmt: off
            (CatalogRequirement.reference, references, neg_references),
            (CatalogRequirement.gs_absicherung, gs_absicherungen, neg_gs_absicherungen),
            (CatalogRequirement.id, ids, neg_ids),
            (CatalogModule.catalog_id, catalog_ids, neg_catalog_ids),
            (CatalogRequirement.catalog_module_id, catalog_module_ids, neg_catalog_module_ids),
            # fmt: on
        )
    )

    # filter for existence
    where_clauses.extend(
        filter_for_existence_many(
            (CatalogRequirement.reference, has_reference),
            (CatalogRequirement.description, has_description),
            (CatalogRequirement.gs_absicherung, has_gs_absicherung),
            (CatalogRequirement.gs_verantwortliche, has_gs_verantwortliche),
        )
    )

    # filter by search string
    if search:
        where_clauses.append(
            search_columns(
                search,
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

    return where_clauses


def get_catalog_requirement_sort(
    sort_by: str | None = None,
    sort_order: constr(pattern=r"^(asc|desc)$") | None = None,
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
    catalog_requirements: CatalogRequirements = Depends(),
) -> Page[CatalogRequirementOutput] | list[CatalogRequirement]:
    catalog_requirements_list = catalog_requirements.list_catalog_requirements(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        return Page[CatalogRequirementOutput](
            items=catalog_requirements_list,
            total_count=catalog_requirements.count_catalog_requirements(where_clauses),
        )
    else:
        return catalog_requirements_list


@router.post(
    "/catalog-modules/{catalog_module_id}/catalog-requirements",
    response_model=CatalogRequirementOutput,
    status_code=201,
)
def create_catalog_requirement(
    catalog_module_id: int,
    catalog_requirement_input: CatalogRequirementInput,
    catalog_modules: CatalogModules = Depends(),
    catalog_requirements: CatalogRequirements = Depends(),
) -> CatalogRequirement:
    return catalog_requirements.create_catalog_requirement(
        catalog_modules.get_catalog_module(catalog_module_id),
        catalog_requirement_input,
    )


@router.get(
    "/catalog-requirements/{catalog_requirement_id}",
    response_model=CatalogRequirementOutput,
)
def get_catalog_requirement(
    catalog_requirement_id: int,
    catalog_requirements: CatalogRequirements = Depends(),
) -> CatalogRequirement:
    return catalog_requirements.get_catalog_requirement(catalog_requirement_id)


@router.put(
    "/catalog-requirements/{catalog_requirement_id}",
    response_model=CatalogRequirementOutput,
)
def update_catalog_requirement(
    catalog_requirement_id: int,
    catalog_requirement_input: CatalogRequirementInput,
    catalog_requirements: CatalogRequirements = Depends(),
) -> CatalogRequirement:
    catalog_requirement = catalog_requirements.get_catalog_requirement(
        catalog_requirement_id
    )
    catalog_requirements.update_catalog_requirement(
        catalog_requirement, catalog_requirement_input
    )
    return catalog_requirement


@router.patch(
    "/catalog-requirements/{catalog_requirement_id}",
    response_model=CatalogRequirementOutput,
)
def patch_catalog_requirement(
    catalog_requirement_id: int,
    catalog_requirement_patch: CatalogRequirementPatch,
    catalog_requirements: CatalogRequirements = Depends(),
) -> CatalogRequirement:
    catalog_requirement = catalog_requirements.get_catalog_requirement(
        catalog_requirement_id
    )
    catalog_requirements.patch_catalog_requirement(
        catalog_requirement, catalog_requirement_patch
    )
    return catalog_requirement


@router.patch(
    "/catalog-requirements",
    response_model=list[CatalogRequirementOutput],
)
def patch_catalog_requirements(
    catalog_requirement_patch: CatalogRequirementPatch,
    where_clauses=Depends(get_catalog_requirement_filters),
    catalog_requirements: CatalogRequirements = Depends(),
) -> list[CatalogRequirement]:
    catalog_requirements_ = catalog_requirements.list_catalog_requirements(
        where_clauses
    )
    for catalog_requirement in catalog_requirements_:
        catalog_requirements.patch_catalog_requirement(
            catalog_requirement, catalog_requirement_patch, skip_flush=True
        )
    catalog_requirements._session.flush()
    return catalog_requirements_


@router.delete("/catalog-requirements/{catalog_requirement_id}", status_code=204)
def delete_catalog_requirement(
    catalog_requirement_id: int,
    catalog_requirements: CatalogRequirements = Depends(),
) -> None:
    catalog_requirement = catalog_requirements.get_catalog_requirement(
        catalog_requirement_id
    )
    catalog_requirements.delete_catalog_requirement(catalog_requirement)


@router.delete("/catalog-requirements", status_code=204)
def delete_catalog_requirements(
    where_clauses=Depends(get_catalog_requirement_filters),
    catalog_requirements: CatalogRequirements = Depends(),
) -> None:
    catalog_requirements_ = catalog_requirements.list_catalog_requirements(
        where_clauses
    )
    for catalog_requirement in catalog_requirements_:
        catalog_requirements.delete_catalog_requirement(
            catalog_requirement, skip_flush=True
        )
    catalog_requirements._session.flush()


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
    catalog_requirements: CatalogRequirements = Depends(),
) -> Page[CatalogRequirementRepresentation] | list[CatalogRequirement]:
    if local_search:
        where_clauses.append(
            search_columns(
                local_search, CatalogRequirement.reference, CatalogRequirement.summary
            )
        )

    catalog_requirements_list = catalog_requirements.list_catalog_requirements(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        return Page[CatalogRequirementRepresentation](
            items=catalog_requirements_list,
            total_count=catalog_requirements.count_catalog_requirements(where_clauses),
        )
    else:
        return catalog_requirements_list


@router.get("/catalog-requirement/field-names", response_model=list[str])
def get_catalog_requirement_field_names(
    where_clauses=Depends(get_catalog_requirement_filters),
    catalog_requirements: CatalogRequirements = Depends(),
) -> set[str]:
    field_names = {"id", "summary", "catalog_module"}
    for field, names in [
        (CatalogRequirement.reference, ["reference"]),
        (CatalogRequirement.description, ["description"]),
        (CatalogRequirement.gs_absicherung, ["gs_absicherung"]),
        (CatalogRequirement.gs_verantwortliche, ["gs_verantwortliche"]),
    ]:
        if catalog_requirements.has_catalog_requirement(
            [filter_for_existence(field, True), *where_clauses]
        ):
            field_names.update(names)
    return field_names


@router.get("/catalog-requirement/references", response_model=Page[str] | list[str])
def get_catalog_requirement_references(
    where_clauses: list[Any] = Depends(get_catalog_requirement_filters),
    local_search: str | None = None,
    page_params=Depends(page_params),
    catalog_requirements: CatalogRequirements = Depends(),
) -> Page[str] | list[str]:
    if local_search:
        where_clauses.append(search_columns(local_search, CatalogRequirement.reference))
    references = catalog_requirements.list_catalog_requirement_values(
        CatalogRequirement.reference, where_clauses, **page_params
    )
    if page_params:
        return Page[str](
            items=references,
            total_count=catalog_requirements.count_catalog_requirement_values(
                CatalogRequirement.reference, where_clauses
            ),
        )
    else:
        return references
