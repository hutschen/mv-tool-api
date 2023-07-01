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

from pydantic import BaseModel, validator

from .common import ETagMixin


class CatalogInput(BaseModel):
    reference: str | None
    title: str
    description: str | None


class CatalogPatch(CatalogInput):
    title: str | None = None

    @validator("title")
    def title_validator(cls, v):
        if not v:
            raise ValueError("title must not be empty")
        return v


class CatalogImport(ETagMixin, CatalogInput):
    id: int | None = None


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
