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

from typing import Callable

from pydantic import PrivateAttr, confloat, constr
from sqlmodel import Field, Relationship, Session, SQLModel, func, or_, select

from .common import CommonFieldsMixin, AbstractComplianceInput
from .jira_ import (
    JiraUser,
    JiraProject,
    JiraIssueType,
    JiraIssueStatus,
    JiraIssueInput,
    JiraIssue,
)
from .measures import (
    AbstractMeasureInput,
    MeasureInput,
    Measure,
    MeasureRepresentation,
    MeasureOutput,
)
from .requirements import (
    AbstractRequirementInput,
    RequirementInput,
    Requirement,
    RequirementRepresentation,
    RequirementOutput,
)
from .catalog_requirements import (
    CatalogRequirementInput,
    CatalogRequirement,
    CatalogRequirementRepresentation,
    CatalogRequirementOutput,
)


class CatalogModuleInput(SQLModel):
    reference: str | None
    title: str
    description: str | None


class CatalogModule(CatalogModuleInput, CommonFieldsMixin, table=True):
    __tablename__ = "catalog_module"
    catalog_requirements: list[CatalogRequirement] = Relationship(
        back_populates="catalog_module",
        sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
    )
    catalog_id: int | None = Field(default=None, foreign_key="catalog.id")
    catalog: "Catalog" = Relationship(
        back_populates="catalog_modules", sa_relationship_kwargs=dict(lazy="joined")
    )


class CatalogInput(SQLModel):
    reference: str | None
    title: str
    description: str | None


class Catalog(CatalogInput, CommonFieldsMixin, table=True):
    __tablename__ = "catalog"
    catalog_modules: list[CatalogModule] = Relationship(
        back_populates="catalog",
        sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
    )


class DocumentInput(SQLModel):
    reference: str | None
    title: str
    description: str | None


class Document(DocumentInput, CommonFieldsMixin, table=True):
    project_id: int | None = Field(default=None, foreign_key="project.id")
    project: "Project" = Relationship(
        back_populates="documents", sa_relationship_kwargs=dict(lazy="joined")
    )
    measures: list[Measure] = Relationship(back_populates="document")


class ProjectInput(SQLModel):
    name: str
    description: str | None
    jira_project_id: str | None


class Project(ProjectInput, CommonFieldsMixin, table=True):
    requirements: list[Requirement] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
    )
    documents: list[Document] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
    )

    _get_jira_project: Callable = PrivateAttr()

    @property
    def jira_project(self) -> JiraProject:
        if self.jira_project_id is None:
            return None

        return getattr(self, "_get_jira_project")(self.jira_project_id)

    @property
    def _compliant_count_query(self):
        return (
            select([func.count()])
            .select_from(Requirement)
            .outerjoin(Measure)
            .where(
                Requirement.project_id == self.id,
                or_(
                    Requirement.compliance_status.in_(("C", "PC")),
                    Requirement.compliance_status.is_(None),
                ),
                or_(
                    Measure.compliance_status.in_(("C", "PC")),
                    Measure.compliance_status.is_(None),
                ),
            )
        )

    @property
    def completion_progress(self) -> float | None:
        session = Session.object_session(self)

        # get the total number of measures in project
        total = session.execute(self._compliant_count_query).scalar()

        # get the number of completed measures in project
        completed_query = self._compliant_count_query.where(
            Measure.completion_status == "completed"
        )
        completed = session.execute(completed_query).scalar()

        return completed / total if total else None

    @property
    def verification_progress(self) -> float | None:
        session = Session.object_session(self)

        # get the total number of measures in project
        total = session.execute(self._compliant_count_query).scalar()

        # get the number of verified measures in project
        verified_query = self._compliant_count_query.where(
            Measure.verification_status == "verified"
        )
        verified = session.execute(verified_query).scalar()

        return verified / total if total else None


class CatalogRepresentation(SQLModel):
    id: int
    reference: str | None
    title: str


class CatalogOutput(CatalogInput):
    id: int


class CatalogModuleRepresentation(SQLModel):
    id: int
    reference: str | None
    title: str


class CatalogModuleOutput(CatalogModuleInput):
    id: int
    catalog: CatalogOutput


class ProjectRepresentation(SQLModel):
    id: int
    name: str


class ProjectOutput(ProjectInput):
    id: int
    jira_project: JiraProject | None
    completion_progress: confloat(ge=0, le=1) | None
    verification_progress: confloat(ge=0, le=1) | None


class DocumentRepresentation(SQLModel):
    id: int
    reference: str | None
    title: str


class DocumentOutput(DocumentInput):
    id: int
    project: ProjectOutput


MeasureOutput.update_forward_refs(
    RequirementOutput=RequirementOutput, DocumentOutput=DocumentOutput
)
RequirementOutput.update_forward_refs(
    ProjectOutput=ProjectOutput, CatalogRequirementOutput=CatalogRequirementOutput
)
CatalogRequirementOutput.update_forward_refs(CatalogModuleOutput=CatalogModuleOutput)
