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

from pydantic import constr
from sqlmodel import Field, Relationship, SQLModel

from .common import CommonFieldsMixin
from .requirements import AbstractRequirementInput, Requirement

if TYPE_CHECKING:
    from .catalog_modules import CatalogModule, CatalogModuleImport, CatalogModuleOutput


class CatalogRequirementInput(AbstractRequirementInput):
    # Special fields for IT Grundschutz Kompendium
    gs_absicherung: constr(regex=r"^(B|S|H)$") | None
    gs_verantwortliche: str | None


class CatalogRequirementImport(SQLModel):
    id: int | None = None
    reference: str | None
    summary: str
    description: str | None
    gs_absicherung: constr(regex=r"^(B|S|H)$") | None
    gs_verantwortliche: str | None
    catalog_module: "CatalogModuleImport | None" = None


class CatalogRequirement(CatalogRequirementInput, CommonFieldsMixin, table=True):
    __tablename__ = "catalog_requirement"
    catalog_module_id: int | None = Field(default=None, foreign_key="catalog_module.id")
    catalog_module: "CatalogModule" = Relationship(
        back_populates="catalog_requirements",
        sa_relationship_kwargs=dict(lazy="joined"),
    )
    requirements: list[Requirement] = Relationship(back_populates="catalog_requirement")


class CatalogRequirementRepresentation(SQLModel):
    id: int
    reference: str | None
    summary: str


class CatalogRequirementOutput(CatalogRequirementInput):
    id: int
    catalog_module: "CatalogModuleOutput"

    # Special fields for IT Grundschutz Kompendium
    gs_absicherung: constr(regex=r"^(B|S|H)$") | None
    gs_verantwortliche: str | None
