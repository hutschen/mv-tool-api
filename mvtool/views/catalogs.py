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

from ..auth import get_jira
from ..database import delete_from_db, get_session, read_from_db
from ..models.catalogs import (
    Catalog,
    CatalogImport,
    CatalogInput,
    CatalogOutput,
    CatalogRepresentation,
)
from ..utils.errors import NotFoundError
from ..utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
    search_columns,
)
from ..utils.iteration import CachedIterable
from ..utils.pagination import Page, page_params

router = APIRouter()


class CatalogsView:
    kwargs = dict(tags=["catalog"])

    def __init__(
        self,
        session: Session = Depends(get_session),
        _=Depends(get_jira),  # get jira to enforce login
    ):
        self._session = session

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

    def create_catalog(
        self, creation: CatalogImport | CatalogInput, skip_flush: bool = False
    ) -> Catalog:
        """Create a catalog from a given creation object."""
        if isinstance(creation, CatalogImport):
            creation.id = None
        catalog = Catalog.from_orm(creation)
        self._session.add(catalog)
        if not skip_flush:
            self._session.flush()
        return catalog

    def get_catalog(self, catalog_id: int) -> Catalog:
        return read_from_db(self._session, Catalog, catalog_id)

    def update_catalog(
        self,
        catalog: Catalog,
        update: CatalogImport | CatalogInput,
        patch: bool = False,
        skip_flush: bool = False,
    ) -> None:
        """Update a catalog with the values from a given update object."""
        for key, value in update.dict(exclude_unset=patch, exclude={"id"}).items():
            setattr(catalog, key, value)
        if not skip_flush:
            self._session.flush()

    def delete_catalog(self, catalog: Catalog, skip_flush: bool = False) -> None:
        return delete_from_db(self._session, catalog, skip_flush)

    def bulk_create_update_catalogs(
        self,
        catalog_imports: Iterable[CatalogImport],
        patch: bool = False,
        skip_flush: bool = False,
    ) -> Iterator[Catalog]:
        """Create or update catalogs in bulk using the provided catalog imports.

        Args:
            catalog_imports (Iterable[CatalogImport]): An iterable of catalog imports
                containing the data for creating or updating catalogs.
            patch (bool): If True, only the fields that are set in the catalog import
                are updated. If False, all fields are updated.
            skip_flush (bool, optional): If True, the changes are not written to the
                database, and an empty list is returned. Defaults to False.

        Returns:
            Iterator[Catalog]: An iterator over the catalogs that were created or
                updated.

        Raises:
            NotFoundError: If a catalog to be updated is not found in the database.
        """
        catalog_imports = CachedIterable(catalog_imports)

        # Get catalogs to be updated from the database
        ids = [c.id for c in catalog_imports if c.id is not None]
        catalogs_to_update = {
            c.id: c for c in (self.list_catalogs([Catalog.id.in_(ids)]) if ids else [])
        }

        # Update catalogs
        for catalog_import in catalog_imports:
            if catalog_import.id is None:
                # Create new catalog
                yield self.create_catalog(catalog_import, skip_flush=True)
            else:
                # Update existing catalog
                catalog = catalogs_to_update.get(catalog_import.id, None)
                if catalog is None:
                    raise NotFoundError(f"No catalog with id={catalog_import.id}.")
                self.update_catalog(
                    catalog, catalog_import, patch=patch, skip_flush=True
                )
                yield catalog

        # Write changes to the database
        if not skip_flush:
            self._session.flush()

    def convert_catalog_imports(
        self, catalog_imports: Iterable[CatalogImport], patch: bool = False
    ) -> dict[str, Catalog]:
        # Map catalog imports to their etags
        catalogs_map = {c.etag: c for c in catalog_imports}

        # Map created and updated catalogs to the etags of their imports
        for etag, catalog in zip(
            catalogs_map.keys(),
            self.bulk_create_update_catalogs(
                catalogs_map.values(), patch=patch, skip_flush=True
            ),
        ):
            catalogs_map[etag] = catalog

        return catalogs_map


def get_catalog_filters(
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

    # filter by values or by ids
    for column, values in (
        (Catalog.id, ids),
        (Catalog.reference, references),
    ):
        if values:
            where_clauses.append(filter_by_values(column, values))

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


@router.post(
    "/catalogs", status_code=201, response_model=CatalogOutput, **CatalogsView.kwargs
)
def create_catalog(
    catalog: CatalogInput,
    catalogs_view: CatalogsView = Depends(),
) -> Catalog:
    return catalogs_view.create_catalog(catalog)


@router.get(
    "/catalogs/{catalog_id}", response_model=CatalogOutput, **CatalogsView.kwargs
)
def get_catalog(catalog_id: int, catalogs_view: CatalogsView = Depends()) -> Catalog:
    return catalogs_view.get_catalog(catalog_id)


@router.put(
    "/catalogs/{catalog_id}", response_model=CatalogOutput, **CatalogsView.kwargs
)
def update_catalog(
    catalog_id: int,
    catalog_input: CatalogInput,
    catalogs_view: CatalogsView = Depends(),
) -> Catalog:
    catalog = catalogs_view.get_catalog(catalog_id)
    catalogs_view.update_catalog(catalog, catalog_input)
    return catalog


@router.delete("/catalogs/{catalog_id}", status_code=204, **CatalogsView.kwargs)
def delete_catalog(
    catalog_id: int,
    catalogs_view: CatalogsView = Depends(),
) -> None:
    catalog = catalogs_view.get_catalog(catalog_id)
    catalogs_view.delete_catalog(catalog)


@router.get(
    "/catalog/representations",
    response_model=Page[CatalogRepresentation] | list[CatalogRepresentation],
    **CatalogsView.kwargs,
)
def get_catalog_representations(
    where_clauses=Depends(get_catalog_filters),
    local_search: str | None = None,
    order_by_clauses=Depends(get_catalog_sort),
    page_params=Depends(page_params),
    catalogs_view: CatalogsView = Depends(),
):
    if local_search:
        where_clauses.append(
            search_columns(local_search, Catalog.reference, Catalog.title)
        )

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
    where_clauses: list[Any] = Depends(get_catalog_filters),
    local_search: str | None = None,
    page_params=Depends(page_params),
    catalogs_view: CatalogsView = Depends(),
):
    if local_search:
        where_clauses.append(search_columns(local_search, Catalog.reference))

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
