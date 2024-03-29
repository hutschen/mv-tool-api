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

from .catalog_modules import (
    CatalogModuleImport,
    CatalogModuleInput,
    CatalogModuleOutput,
    CatalogModuleRepresentation,
)
from .catalog_requirements import (
    CatalogRequirementImport,
    CatalogRequirementInput,
    CatalogRequirementOutput,
    CatalogRequirementRepresentation,
)
from .catalogs import (
    CatalogImport,
    CatalogInput,
    CatalogOutput,
    CatalogRepresentation,
)
from .documents import (
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
    MeasureImport,
    MeasureInput,
    MeasureOutput,
    MeasureRepresentation,
)
from .projects import (
    ProjectImport,
    ProjectInput,
    ProjectOutput,
    ProjectRepresentation,
)
from .requirements import (
    AbstractRequirementInput,
    RequirementImport,
    RequirementInput,
    RequirementOutput,
    RequirementRepresentation,
)

# Update forward references for catalog module models
CatalogModuleImport.model_rebuild(_types_namespace=dict(CatalogImport=CatalogImport))
CatalogModuleOutput.model_rebuild(_types_namespace=dict(CatalogOutput=CatalogOutput))

# Update forward references for catalog requirement models
CatalogRequirementImport.model_rebuild(
    _types_namespace=dict(CatalogModuleImport=CatalogModuleImport)
)
CatalogRequirementOutput.model_rebuild(
    _types_namespace=dict(CatalogModuleOutput=CatalogModuleOutput)
)

# Update forward references for requirement models
RequirementImport.model_rebuild(
    _types_namespace=dict(
        CatalogRequirementImport=CatalogRequirementImport, ProjectImport=ProjectImport
    )
)
RequirementOutput.model_rebuild(
    _types_namespace=dict(
        ProjectOutput=ProjectOutput, CatalogRequirementOutput=CatalogRequirementOutput
    )
)

# Update forward references for document models
DocumentImport.model_rebuild(_types_namespace=dict(ProjectImport=ProjectImport))
DocumentOutput.model_rebuild(_types_namespace=dict(ProjectOutput=ProjectOutput))

# Update forward references for measure models
MeasureImport.model_rebuild(
    _types_namespace=dict(
        RequirementImport=RequirementImport, DocumentImport=DocumentImport
    )
)
# Measure.update_forward_refs(Requirement=Requirement, Document=Document)
MeasureOutput.model_rebuild(
    _types_namespace=dict(
        RequirementOutput=RequirementOutput, DocumentOutput=DocumentOutput
    )
)
