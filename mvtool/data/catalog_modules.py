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

from fastapi import Depends
from sqlmodel import Column, Session, func, select
from sqlmodel.sql.expression import Select

from ..database import delete_from_db, get_session, read_from_db
from ..models.catalog_modules import (
    CatalogModule,
    CatalogModuleImport,
    CatalogModuleInput,
)
from ..models.catalogs import Catalog
from ..utils.errors import NotFoundError
from ..utils.etag_map import get_from_etag_map
from ..utils.fallback import fallback
from ..utils.filtering import filter_for_existence
from ..utils.iteration import CachedIterable
from .catalogs import Catalogs


class CatalogModules:
    def __init__(
        self,
        catalogs: Catalogs = Depends(Catalogs),
        session: Session = Depends(get_session),
    ):
        self._catalogs = catalogs
        self._session = session

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
        return self._session.execute(query).scalars().all()

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
            [filter_for_existence(column), *(where_clauses or [])],
            offset=offset,
            limit=limit,
        )
        return self._session.execute(query).scalars().all()

    def count_catalog_module_values(
        self, column: Column, where_clauses: list[Any] | None = None
    ) -> int:
        query = self._modify_catalog_modules_query(
            select([func.count(func.distinct(column))]).select_from(CatalogModule),
            [filter_for_existence(column), *(where_clauses or [])],
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

    def delete_catalog_module(
        self, catalog_module: CatalogModule, skip_flush: bool = False
    ) -> None:
        return delete_from_db(self._session, catalog_module, skip_flush)

    def bulk_create_update_catalog_modules(
        self,
        catalog_module_imports: Iterable[CatalogModuleImport],
        fallback_catalog: Catalog | None = None,
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
                    fallback(
                        catalog, fallback_catalog, "No fallback catalog provided."
                    ),
                    catalog_module_import,
                    skip_flush=True,
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
                if catalog is not None:
                    catalog_module.catalog = catalog
                yield catalog_module

        if not skip_flush:
            self._session.flush()

    def convert_catalog_module_imports(
        self,
        catalog_module_imports: Iterable[CatalogModuleImport],
        fallback_catalog: Catalog | None = None,
        patch: bool = False,
    ) -> dict[int, CatalogModule]:
        # Map catalog module imports to their etags
        catalog_modules_map = {c.etag: c for c in catalog_module_imports}

        # Map created and updated catalog modules to the etags of their imports
        for etag, catalog_module in zip(
            catalog_modules_map.keys(),
            self.bulk_create_update_catalog_modules(
                catalog_modules_map.values(),
                fallback_catalog,
                patch=patch,
                skip_flush=True,
            ),
        ):
            catalog_modules_map[etag] = catalog_module

        return catalog_modules_map
