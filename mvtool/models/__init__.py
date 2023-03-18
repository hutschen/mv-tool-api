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
    CatalogModuleImport,
    CatalogModuleInput,
    CatalogModuleOutput,
    CatalogModuleRepresentation,
)
from .catalog_requirements import (
    CatalogRequirement,
    CatalogRequirementImport,
    CatalogRequirementInput,
    CatalogRequirementOutput,
    CatalogRequirementRepresentation,
)
from .catalogs import (
    Catalog,
    CatalogImport,
    CatalogInput,
    CatalogOutput,
    CatalogRepresentation,
)
from .documents import (
    Document,
    DocumentImport,
    DocumentInput,
    DocumentOutput,
    DocumentRepresentation,
)
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
    MeasureImport,
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
    RequirementImport,
    RequirementInput,
    RequirementOutput,
    RequirementRepresentation,
)

# Update forward references for catalog module models
CatalogModuleImport.update_forward_refs(CatalogImport=CatalogImport)
CatalogModule.update_forward_refs(Catalog=Catalog)
CatalogModuleOutput.update_forward_refs(CatalogOutput=CatalogOutput)

# Update forward references for catalog requirement models
CatalogRequirementImport.update_forward_refs(CatalogModuleImport=CatalogModuleImport)
CatalogRequirement.update_forward_refs(CatalogModule=CatalogModule)
CatalogRequirementOutput.update_forward_refs(CatalogModuleOutput=CatalogModuleOutput)

# Update forward references for requirement models
RequirementImport.update_forward_refs(
    CatalogRequirementImport=CatalogRequirementImport, ProjectImport=ProjectImport
)
Requirement.update_forward_refs(CatalogRequirement=CatalogRequirement)
RequirementOutput.update_forward_refs(
    ProjectOutput=ProjectOutput, CatalogRequirementOutput=CatalogRequirementOutput
)

# Update forward references for document models
DocumentImport.update_forward_refs(ProjectImport=ProjectImport)
Document.update_forward_refs(Project=Project)
DocumentOutput.update_forward_refs(ProjectOutput=ProjectOutput)

# Update forward references for measure models
MeasureImport.update_forward_refs(
    RequirementImport=RequirementImport, DocumentImport=DocumentImport
)
Measure.update_forward_refs(Requirement=Requirement, Document=Document)
MeasureOutput.update_forward_refs(
    RequirementOutput=RequirementOutput, DocumentOutput=DocumentOutput
)
