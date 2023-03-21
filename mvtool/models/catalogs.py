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


from sqlmodel import Relationship, SQLModel

from .catalog_modules import CatalogModule
from .common import CommonFieldsMixin, ETagMixin


class CatalogInput(SQLModel):
    reference: str | None
    title: str
    description: str | None


class CatalogImport(ETagMixin):
    id: int | None = None
    reference: str | None
    title: str
    description: str | None


class Catalog(CatalogInput, CommonFieldsMixin, table=True):
    __tablename__ = "catalog"
    catalog_modules: list[CatalogModule] = Relationship(
        back_populates="catalog",
        sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
    )


class CatalogRepresentation(SQLModel):
    id: int
    reference: str | None
    title: str


class CatalogOutput(CatalogInput):
    id: int
