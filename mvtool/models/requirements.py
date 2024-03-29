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

from .common import (
    AbstractComplianceInput,
    AbstractProgressCountsOutput,
    ETagMixin,
    AutoNumber,
)

if TYPE_CHECKING:
    from .catalog_requirements import CatalogRequirementImport, CatalogRequirementOutput
    from .projects import ProjectImport, ProjectOutput


class AbstractRequirementInput(BaseModel):
    reference: str | None = None
    summary: str
    description: str | None = None


class RequirementInput(AbstractRequirementInput, AbstractComplianceInput):
    model_config = ConfigDict(from_attributes=True)

    catalog_requirement_id: int | None = None
    target_object: str | None = None
    milestone: str | None = None


class RequirementPatch(RequirementInput):
    summary: str | None = None

    @field_validator("summary")
    def summary_validator(cls, v):
        if not v:
            raise ValueError("summary must not be empty")
        return v


class RequirementPatchMany(RequirementPatch):
    reference: str | AutoNumber | None = None

    def to_patch(self, counter: int) -> RequirementPatch:
        items = self.model_dump(exclude_unset=True)
        if isinstance(self.reference, AutoNumber):
            items["reference"] = self.reference.to_value(counter)
        return RequirementPatch(**items)


class RequirementImport(ETagMixin, AbstractRequirementInput, AbstractComplianceInput):
    id: int | None = None
    catalog_requirement: "CatalogRequirementImport | None" = None
    project: "ProjectImport | None" = None
    target_object: str | None = None
    milestone: str | None = None


class RequirementRepresentation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str | None
    summary: str


class RequirementOutput(AbstractProgressCountsOutput, AbstractRequirementInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project: "ProjectOutput"
    catalog_requirement: "CatalogRequirementOutput | None"
    target_object: str | None
    milestone: str | None
    compliance_status: str | None
    compliance_status_hint: str | None
    compliance_comment: str | None
