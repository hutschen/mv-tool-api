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
from sqlmodel import Column, or_, select

from mvtool.utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
)

from ..errors import NotFoundError
from ..database import CRUDOperations
from ..models import (
    Catalog,
    CatalogModule,
    CatalogRequirement,
    CatalogRequirementInput,
    CatalogRequirementOutput,
)
from .catalog_modules import CatalogModulesView

router = APIRouter()


@cbv(router)
class CatalogRequirementsView:
    kwargs = dict(tags=["catalog-requirement"])

    def __init__(
        self,
        catalog_modules: CatalogModulesView = Depends(CatalogModulesView),
        crud: CRUDOperations[CatalogRequirement] = Depends(CRUDOperations),
    ):
        self._catalog_modules = catalog_modules
        self._crud = crud
        self._session = self._crud.session

    @router.get(
        "/catalog-modules/{catalog_module_id}/catalog-requirements",
        response_model=list[CatalogRequirementOutput],
        **kwargs,
    )
    def list_catalog_requirements(
        self, catalog_module_id: int
    ) -> list[CatalogRequirement]:
        return self.query_catalog_requirements(
            CatalogRequirement.catalog_module_id == catalog_module_id
        )

    def query_catalog_requirements(
        self, *whereclauses: Any
    ) -> list[CatalogRequirement]:
        return self._session.exec(
            select(CatalogRequirement)
            .where(*whereclauses)
            .order_by(CatalogRequirement.id)
        ).all()

    @router.post(
        "/catalog-modules/{catalog_module_id}/catalog-requirements",
        response_model=CatalogRequirementOutput,
        status_code=201,
        **kwargs,
    )
    def create_catalog_requirement(
        self, catalog_module_id: int, catalog_requirement_input: CatalogRequirementInput
    ) -> CatalogRequirement:
        catalog_requirement = CatalogRequirement.from_orm(catalog_requirement_input)
        catalog_requirement.catalog_module = self._catalog_modules.get_catalog_module(
            catalog_module_id
        )
        return self._crud.create_in_db(catalog_requirement)

    @router.get(
        "/catalog-requirements/{catalog_requirement_id}",
        response_model=CatalogRequirementOutput,
        **kwargs,
    )
    def get_catalog_requirement(
        self, catalog_requirement_id: int
    ) -> CatalogRequirement:
        return self._crud.read_from_db(CatalogRequirement, catalog_requirement_id)

    def check_catalog_requirement_id(
        self, catalog_requirement_id: int | None
    ) -> CatalogRequirement | None:
        if catalog_requirement_id is not None:
            return self.get_catalog_requirement(catalog_requirement_id)

    @router.put(
        "/catalog-requirements/{catalog_requirement_id}",
        response_model=CatalogRequirementOutput,
        **kwargs,
    )
    def update_catalog_requirement(
        self,
        catalog_requirement_id: int,
        catalog_requirement_input: CatalogRequirementInput,
    ) -> CatalogRequirement:
        catalog_requirement = self._session.get(
            CatalogRequirement, catalog_requirement_id
        )
        if not catalog_requirement:
            cls_name = CatalogRequirement.__name__
            raise NotFoundError(f"No {cls_name} with id={catalog_requirement_id}.")
        for key, value in catalog_requirement_input.dict().items():
            setattr(catalog_requirement, key, value)
        self._session.flush()
        return catalog_requirement

    @router.delete(
        "/catalog-requirements/{catalog_requirement_id}",
        status_code=204,
        **kwargs,
    )
    def delete_catalog_requirement(self, catalog_requirement_id: int) -> None:
        return self._crud.delete_from_db(CatalogRequirement, catalog_requirement_id)


def get_catalog_requirement_filters(
    # filter by pattern
    reference: str | None = None,
    summary: str | None = None,
    description: str | None = None,
    gs_absicherung: str | None = None,
    gs_verantwortliche: str | None = None,
    #
    # filter by values
    references: list[str] | None = None,
    gs_absicherungen: list[str] | None = None,
    #
    # filter by ids
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
