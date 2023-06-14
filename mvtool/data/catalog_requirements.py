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
from sqlalchemy import Column, func
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select, select

from ..db.database import delete_from_db, get_session, read_from_db
from ..models.catalog_modules import CatalogModule
from ..models.catalog_requirements import (
    CatalogRequirement,
    CatalogRequirementImport,
    CatalogRequirementInput,
)
from ..models.catalogs import Catalog
from ..utils.errors import NotFoundError
from ..utils.etag_map import get_from_etag_map
from ..utils.fallback import fallback
from ..utils.filtering import filter_for_existence
from ..utils.iteration import CachedIterable
from .catalog_modules import CatalogModules


class CatalogRequirements:
    def __init__(
        self,
        catalog_modules: CatalogModules = Depends(CatalogModules),
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
        return self._session.execute(query).scalars().all()

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
            [filter_for_existence(column), *(where_clauses or [])],
            offset=offset,
            limit=limit,
        )
        return self._session.execute(query).scalars().all()

    def count_catalog_requirement_values(
        self, column: Column, where_clauses: list[Any] | None = None
    ) -> int:
        query = self._modify_catalog_requirements_query(
            select([func.count(func.distinct(column))]).select_from(CatalogRequirement),
            [filter_for_existence(column), *(where_clauses or [])],
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

    def delete_catalog_requirement(
        self, catalog_requirement: CatalogRequirement, skip_flush: bool = False
    ) -> None:
        return delete_from_db(self._session, catalog_requirement, skip_flush)

    def bulk_create_update_catalog_requirements(
        self,
        catalog_requirement_imports: Iterable[CatalogRequirementImport],
        fallback_catalog_module: CatalogModule | None = None,
        patch: bool = False,
        skip_flush: bool = False,
    ) -> Iterator[CatalogRequirement]:
        catalog_requirement_imports = CachedIterable(catalog_requirement_imports)

        # Convert catalog module imports to catalog modules
        catalog_modules_map = self._catalog_modules.convert_catalog_module_imports(
            (
                c.catalog_module
                for c in catalog_requirement_imports
                if c.catalog_module is not None
            ),
            fallback_catalog_module.catalog if fallback_catalog_module else None,
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
                    fallback(
                        catalog_module,
                        fallback_catalog_module,
                        "No fallback catalog module provided.",
                    ),
                    catalog_requirement_import,
                    skip_flush=True,
                )
            else:
                # Update existing catalog requirement
                catalog_requirement = catalog_requirements_to_update.get(
                    catalog_requirement_import.id
                )
                if catalog_requirement is None:
                    raise NotFoundError(
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

    def convert_catalog_requirement_imports(
        self,
        catalog_requirement_imports: Iterable[CatalogRequirementImport],
        fallback_catalog_module: CatalogModule | None = None,
        patch: bool = False,
    ) -> dict[str, CatalogRequirement]:
        # Map catalog requirement imports to their etags
        catalog_requirements_map = {r.etag: r for r in catalog_requirement_imports}

        # Map created and updated catalog requirements to the etags of their imports
        for etag, catalog_requirement in zip(
            catalog_requirements_map.keys(),
            self.bulk_create_update_catalog_requirements(
                catalog_requirements_map.values(),
                fallback_catalog_module,
                patch=patch,
                skip_flush=True,
            ),
        ):
            catalog_requirements_map[etag] = catalog_requirement

        return catalog_requirements_map
