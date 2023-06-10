# coding: utf-8
#
# Copyright (C) 2023 Helmar Hutschenreuter
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


from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from .catalog_requirements import CatalogRequirement
from .common import CommonFieldsMixin, ETagMixin

if TYPE_CHECKING:
    from . import Catalog, CatalogImport, CatalogOutput


class CatalogModuleInput(SQLModel):
    reference: str | None
    title: str
    description: str | None


class CatalogModuleImport(ETagMixin, CatalogModuleInput):
    id: int | None = None
    catalog: "CatalogImport | None" = None


class CatalogModule(CommonFieldsMixin, table=True):
    __tablename__ = "catalog_module"
    reference: str | None
    title: str
    description: str | None
    catalog_requirements: list[CatalogRequirement] = Relationship(
        back_populates="catalog_module",
        sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
    )
    catalog_id: int | None = Field(default=None, foreign_key="catalog.id")
    catalog: "Catalog" = Relationship(
        back_populates="catalog_modules", sa_relationship_kwargs=dict(lazy="joined")
    )


class CatalogModuleRepresentation(SQLModel):
    id: int
    reference: str | None
    title: str


class CatalogModuleOutput(CatalogModuleInput):
    id: int
    catalog: "CatalogOutput"
