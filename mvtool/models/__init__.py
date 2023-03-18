# coding: utf-8
#
# Copyright (C) 2022 Helmar Hutschenreuter
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

from sqlmodel import SQLModel

from .catalog_modules import (
    CatalogModule,
    CatalogModuleInput,
    CatalogModuleOutput,
    CatalogModuleRepresentation,
)
from .catalog_requirements import (
    CatalogRequirement,
    CatalogRequirementInput,
    CatalogRequirementOutput,
    CatalogRequirementRepresentation,
)
from .catalogs import Catalog, CatalogInput, CatalogOutput, CatalogRepresentation
from .common import AbstractComplianceInput, CommonFieldsMixin
from .documents import Document, DocumentInput, DocumentOutput, DocumentRepresentation
from .jira_ import (
    JiraIssue,
    JiraIssueImport,
    JiraIssueInput,
    JiraIssueStatus,
    JiraIssueType,
    JiraProject,
    JiraProjectImport,
    JiraUser,
)
from .measures import (
    AbstractMeasureInput,
    Measure,
    MeasureInput,
    MeasureOutput,
    MeasureRepresentation,
)
from .projects import (
    Project,
    ProjectImport,
    ProjectInput,
    ProjectOutput,
    ProjectRepresentation,
)
from .requirements import (
    AbstractRequirementInput,
    Requirement,
    RequirementInput,
    RequirementOutput,
    RequirementRepresentation,
)

MeasureOutput.update_forward_refs(
    RequirementOutput=RequirementOutput, DocumentOutput=DocumentOutput
)
RequirementOutput.update_forward_refs(
    ProjectOutput=ProjectOutput, CatalogRequirementOutput=CatalogRequirementOutput
)
CatalogRequirementOutput.update_forward_refs(CatalogModuleOutput=CatalogModuleOutput)
CatalogModuleOutput.update_forward_refs(CatalogOutput=CatalogOutput)
DocumentOutput.update_forward_refs(ProjectOutput=ProjectOutput)
