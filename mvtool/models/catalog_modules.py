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

from pydantic import BaseModel, ConfigDict, field_validator

from .common import ETagMixin, AutoNumber

if TYPE_CHECKING:
    from . import CatalogImport, CatalogOutput


class CatalogModuleInput(BaseModel):
    reference: str | None = None
    title: str
    description: str | None = None


class CatalogModulePatch(CatalogModuleInput):
    title: str | None = None

    @field_validator("title")
    def title_validator(cls, v):
        if not v:
            raise ValueError("title must not be empty")
        return v


class CatalogModulePatchMany(CatalogModulePatch):
    reference: str | AutoNumber | None = None

    def to_patch(self, counter: int) -> CatalogModulePatch:
        items = self.model_dump(exclude_unset=True)
        if isinstance(self.reference, AutoNumber):
            items["reference"] = self.reference.to_value(counter)
        return CatalogModulePatch(**items)


class CatalogModuleImport(ETagMixin, CatalogModuleInput):
    id: int | None = None
    catalog: "CatalogImport | None" = None


class CatalogModuleRepresentation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str | None
    title: str


class CatalogModuleOutput(CatalogModuleInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    catalog: "CatalogOutput"
