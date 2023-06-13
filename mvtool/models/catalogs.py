# -*- coding: utf-8 -*-
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

from pydantic import BaseModel
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from ..database import Base
from .common import CommonFieldsMixin, ETagMixin


class CatalogInput(BaseModel):
    reference: str | None
    title: str
    description: str | None


class CatalogImport(ETagMixin, CatalogInput):
    id: int | None = None


class Catalog(CommonFieldsMixin, Base):
    __tablename__ = "catalog"
    reference = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    catalog_modules = relationship(
        "CatalogModule", back_populates="catalog", cascade="all,delete,delete-orphan"
    )


class CatalogRepresentation(BaseModel):
    class Config:
        orm_mode = True

    id: int
    reference: str | None
    title: str


class CatalogOutput(CatalogInput):
    class Config:
        orm_mode = True

    id: int
