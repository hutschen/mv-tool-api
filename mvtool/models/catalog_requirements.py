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


from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from .common import AutoNumber, ETagMixin
from .requirements import AbstractRequirementInput

if TYPE_CHECKING:
    from .catalog_modules import CatalogModuleImport, CatalogModuleOutput

GSAbsicherung = Annotated[str, StringConstraints(pattern=r"^(B|S|H)$")]


class CatalogRequirementInput(AbstractRequirementInput):
    # Special fields for IT Grundschutz Kompendium
    gs_absicherung: GSAbsicherung | None = None
    gs_verantwortliche: str | None = None


class CatalogRequirementPatch(CatalogRequirementInput):
    summary: str | None = None

    @field_validator("summary")
    def summary_validator(cls, v):
        if not v:
            raise ValueError("summary must not be empty")
        return v


class CatalogRequirementPatchMany(CatalogRequirementPatch):
    reference: str | AutoNumber | None = None

    def to_patch(self, counter: int) -> CatalogRequirementPatch:
        items = self.model_dump(exclude_unset=True)
        if isinstance(self.reference, AutoNumber):
            items["reference"] = self.reference.to_value(counter)
        return CatalogRequirementPatch(**items)


class CatalogRequirementImport(ETagMixin, CatalogRequirementInput):
    id: int | None = None
    catalog_module: "CatalogModuleImport | None" = None


class CatalogRequirementRepresentation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str | None
    summary: str


class CatalogRequirementOutput(CatalogRequirementInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    catalog_module: "CatalogModuleOutput"

    # Special fields for IT Grundschutz Kompendium
    gs_absicherung: GSAbsicherung | None
    gs_verantwortliche: str | None
