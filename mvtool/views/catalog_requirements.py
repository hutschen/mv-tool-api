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
from pydantic import constr
from sqlmodel import Column, Session, func, or_, select
from sqlmodel.sql.expression import Select

from ..database import delete_from_db, get_session, read_from_db
from ..models.catalog_modules import CatalogModule
from ..models.catalog_requirements import (
    CatalogRequirement,
    CatalogRequirementImport,
    CatalogRequirementInput,
    CatalogRequirementOutput,
    CatalogRequirementRepresentation,
)
from ..models.catalogs import Catalog
from ..utils.etag_map import get_from_etag_map
from ..utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
    search_columns,
)
from ..utils.iteration import CachedIterable
from ..utils.pagination import Page, page_params
from .catalog_modules import CatalogModulesView

router = APIRouter()


class CatalogRequirementsView:
    kwargs = dict(tags=["catalog-requirement"])

    def __init__(
        self,
        catalog_modules: CatalogModulesView = Depends(CatalogModulesView),
        session: Session = Depends(get_session),
    ):
        self._catalog_modules = catalog_modules
        self._session = session

    @staticmethod
    def _modify_catalog_requirements_query(
        query: Select,
        where_clauses: list[Any] | None = None,
        order_by_clauses: list[Any] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Select:
        """Modify a query to include all required joins, clauses and offset and limit."""
        query = query.join(CatalogModule).join(Catalog)
        if where_clauses:
            query = query.where(*where_clauses)
        if order_by_clauses:
            query = query.order_by(*order_by_clauses)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query

    def list_catalog_requirements(
        self,
        where_clauses: list[Any] | None = None,
        order_by_clauses: list[Any] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[CatalogRequirement]:
        query = self._modify_catalog_requirements_query(
            select(CatalogRequirement),
            where_clauses,
            order_by_clauses or [CatalogRequirement.id],
            offset,
            limit,
        )
        return self._session.exec(query).all()

    def count_catalog_requirements(self, where_clauses: list[Any] | None = None) -> int:
        query = self._modify_catalog_requirements_query(
            select([func.count()]).select_from(CatalogRequirement),
            where_clauses,
        )
        return self._session.execute(query).scalar()

    def list_catalog_requirement_values(
        self,
        column: Column,
        where_clauses: list[Any] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        query = self._modify_catalog_requirements_query(
            select([func.distinct(column)]).select_from(CatalogRequirement),
            [filter_for_existence(column), *where_clauses],
            offset=offset,
            limit=limit,
        )
        return self._session.exec(query).all()

    def count_catalog_requirement_values(
        self, column: Column, where_clauses: list[Any] | None = None
    ) -> int:
        query = self._modify_catalog_requirements_query(
            select([func.count(func.distinct(column))]).select_from(CatalogRequirement),
            [filter_for_existence(column), *where_clauses],
        )
        return self._session.execute(query).scalar()

    def create_catalog_requirement(
        self,
        catalog_module: CatalogModule,
        creation: CatalogRequirementInput | CatalogRequirementImport,
        skip_flush: bool = False,
    ) -> CatalogRequirement:
        catalog_requirement = CatalogRequirement(
            **creation.dict(exclude={"id", "catalog_module"})
        )
        catalog_requirement.catalog_module = catalog_module
        self._session.add(catalog_requirement)
        if not skip_flush:
            self._session.flush()
        return catalog_requirement

    def get_catalog_requirement(
        self, catalog_requirement_id: int
    ) -> CatalogRequirement:
        return read_from_db(self._session, CatalogRequirement, catalog_requirement_id)

    def check_catalog_requirement_id(
        self, catalog_requirement_id: int | None
    ) -> CatalogRequirement | None:
        if catalog_requirement_id is not None:
            return self.get_catalog_requirement(catalog_requirement_id)

    def update_catalog_requirement(
        self,
        catalog_requirement: CatalogRequirement,
        update: CatalogRequirementInput | CatalogRequirementImport,
        patch: bool = False,
        skip_flush: bool = False,
    ) -> None:
        for key, value in update.dict(
            exclude_unset=patch, exclude={"id", "catalog_module"}
        ).items():
            setattr(catalog_requirement, key, value)

        if not skip_flush:
            self._session.flush()

    def bulk_create_update_catalog_requirements(
        self,
        fallback_catalog_module: CatalogModule,
        catalog_requirement_imports: Iterable[CatalogRequirementImport],
        patch: bool = False,
        skip_flush: bool = False,
    ) -> Iterator[CatalogRequirement]:
        catalog_requirement_imports = CachedIterable(catalog_requirement_imports)

        # Convert catalog module imports to catalog modules
        catalog_modules_map = self._catalog_modules.convert_catalog_module_imports(
            fallback_catalog_module.catalog,
            (
                c.catalog_module
                for c in catalog_requirement_imports
                if c.catalog_module is not None
            ),
            patch=patch,
        )

        # Get catalog requirements to be updated from database
        ids = [c.id for c in catalog_requirement_imports if c.id is not None]
        catalog_requirements_to_update = {
            c.id: c
            for c in (
                self.list_catalog_requirements([CatalogRequirement.id.in_(ids)])
                if ids
                else []
            )
        }

        # Create or update catalog requirements
        for catalog_requirement_import in catalog_requirement_imports:
            catalog_module = get_from_etag_map(
                catalog_modules_map, catalog_requirement_import.catalog_module
            )

            if catalog_requirement_import.id is None:
                # Create new catalog requirement
                yield self.create_catalog_requirement(
                    catalog_module or fallback_catalog_module,
                    catalog_requirement_import,
                    skip_flush=True,
                )
            else:
                # Update existing catalog requirement
                catalog_requirement = catalog_requirements_to_update.get(
                    catalog_requirement_import.id
                )
                if catalog_requirement is None:
                    raise ValueError(
                        f"No catalog requirement with id={catalog_requirement_import.id}."
                    )
                self.update_catalog_requirement(
                    catalog_requirement,
                    catalog_requirement_import,
                    patch,
                    skip_flush=True,
                )
                if catalog_module is not None:
                    catalog_requirement.catalog_module = catalog_module
                yield catalog_requirement

        if not skip_flush:
            self._session.flush()

    def delete_catalog_requirement(
        self, catalog_requirement: CatalogRequirement, skip_flush: bool = False
    ) -> None:
        return delete_from_db(self._session, catalog_requirement, skip_flush)

    def convert_catalog_requirement_imports(
        self,
        catalog_requirement_imports: Iterable[CatalogRequirementImport],
        patch: bool = False,
    ) -> dict[str, CatalogRequirement]:
        # Map catalog requirement imports to their etags
        catalog_requirements_map = {r.etag: r for r in catalog_requirement_imports}

        # Map created and updated catalog requirements to the etags of their imports
        for etag, catalog_requirement in zip(
            catalog_requirements_map.keys(),
            self.bulk_create_update_catalog_requirements(
                catalog_requirements_map.values(), patch=patch, skip_flush=True
            ),
        ):
            catalog_requirements_map[etag] = catalog_requirement

        return catalog_requirements_map


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


@router.get(
    "/catalog-requirements",
    response_model=Page[CatalogRequirementOutput] | list[CatalogRequirementOutput],
    **CatalogRequirementsView.kwargs,
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
    **CatalogRequirementsView.kwargs,
)
def create_catalog_requirement(
    catalog_module_id: int,
    catalog_requirement_input: CatalogRequirementInput,
    catalog_modules_view: CatalogModulesView = Depends(),
    catalog_requirements_view: CatalogRequirementsView = Depends(),
) -> CatalogRequirement:
    catalog_module = catalog_modules_view.get_catalog_module(catalog_module_id)
    return catalog_requirements_view.create_catalog_requirement(
        catalog_module, catalog_requirement_input
    )


@router.get(
    "/catalog-requirements/{catalog_requirement_id}",
    response_model=CatalogRequirementOutput,
    **CatalogRequirementsView.kwargs,
)
def get_catalog_requirement(
    catalog_requirement_id: int,
    catalog_requirements_view: CatalogRequirementsView = Depends(),
) -> CatalogRequirement:
    return catalog_requirements_view.get_catalog_requirement(catalog_requirement_id)


@router.put(
    "/catalog-requirements/{catalog_requirement_id}",
    response_model=CatalogRequirementOutput,
    **CatalogRequirementsView.kwargs,
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


@router.delete(
    "/catalog-requirements/{catalog_requirement_id}",
    status_code=204,
    **CatalogRequirementsView.kwargs,
)
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
    **CatalogRequirementsView.kwargs,
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


@router.get(
    "/catalog-requirement/field-names",
    response_model=list[str],
    **CatalogRequirementsView.kwargs,
)
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


@router.get(
    "/catalog-requirement/references",
    response_model=Page[str] | list[str],
    **CatalogRequirementsView.kwargs,
)
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
