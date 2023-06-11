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

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlmodel import SQLModel

from ..database import Base
from .common import CommonFieldsMixin, ETagMixin

if TYPE_CHECKING:
    from . import CatalogImport, CatalogOutput


class CatalogModuleInput(SQLModel):
    reference: str | None
    title: str
    description: str | None


class CatalogModuleImport(ETagMixin, CatalogModuleInput):
    id: int | None = None
    catalog: "CatalogImport | None" = None


class CatalogModule(CommonFieldsMixin, Base):
    __tablename__ = "catalog_module"
    reference = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    catalog_requirements = relationship(
        "CatalogRequirement",
        back_populates="catalog_module",
        cascade="all,delete,delete-orphan",
    )
    catalog_id = Column(Integer, ForeignKey("catalog.id"), nullable=True)
    catalog = relationship("Catalog", back_populates="catalog_modules", lazy="joined")


class CatalogModuleRepresentation(SQLModel):
    id: int
    reference: str | None
    title: str


class CatalogModuleOutput(CatalogModuleInput):
    id: int
    catalog: "CatalogOutput"
