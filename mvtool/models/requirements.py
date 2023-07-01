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

from pydantic import BaseModel, confloat, validator

from .common import AbstractComplianceInput, ETagMixin

if TYPE_CHECKING:
    from .catalog_requirements import CatalogRequirementImport, CatalogRequirementOutput
    from .projects import ProjectImport, ProjectOutput


class AbstractRequirementInput(BaseModel):
    reference: str | None
    summary: str
    description: str | None


class RequirementInput(AbstractRequirementInput, AbstractComplianceInput):
    # Enable ORM mode to create requirement inputs from catalog requirements
    class Config:
        orm_mode = True

    catalog_requirement_id: int | None
    target_object: str | None
    milestone: str | None


class RequirementPatch(RequirementInput):
    summary: str | None = None

    @validator("summary")
    def summary_validator(cls, v):
        if not v:
            raise ValueError("summary must not be empty")
        return v


class RequirementImport(ETagMixin, AbstractRequirementInput, AbstractComplianceInput):
    id: int | None = None
    catalog_requirement: "CatalogRequirementImport | None"
    project: "ProjectImport | None"
    target_object: str | None
    milestone: str | None


class RequirementRepresentation(BaseModel):
    class Config:
        orm_mode = True

    id: int
    reference: str | None
    summary: str


class RequirementOutput(AbstractRequirementInput):
    class Config:
        orm_mode = True

    id: int
    project: "ProjectOutput"
    catalog_requirement: "CatalogRequirementOutput | None"
    target_object: str | None
    milestone: str | None
    compliance_status: str | None
    compliance_status_hint: str | None
    compliance_comment: str | None
    completion_progress: confloat(ge=0, le=1) | None
    verification_progress: confloat(ge=0, le=1) | None
