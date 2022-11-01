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

from datetime import datetime
from typing import Callable
from pydantic import PrivateAttr, confloat, constr, validator
from sqlmodel import SQLModel, Field, Relationship, Session, select, func, or_


class CommonFieldsMixin(SQLModel):
    id: int = Field(default=None, primary_key=True)
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs=dict(onupdate=datetime.utcnow),
    )


class JiraUser(SQLModel):
    display_name: str
    email_address: str


class JiraProject(SQLModel):
    id: str
    key: str
    name: str
    url: str


class JiraIssueType(SQLModel):
    id: str
    name: str


class JiraIssueStatus(SQLModel):
    name: str
    color_name: str
    completed: bool


class JiraIssueInput(SQLModel):
    summary: str
    description: str | None
    issuetype_id: str


class JiraIssue(JiraIssueInput):
    id: str
    key: str
    project_id: str
    status: JiraIssueStatus
    url: str


class MeasureInput(SQLModel):
    summary: str
    description: str | None
    completed: bool = False
    document_id: int | None
    jira_issue_id: str | None


class Measure(MeasureInput, CommonFieldsMixin, table=True):
    requirement_id: int | None = Field(default=None, foreign_key="requirement.id")
    requirement: "Requirement" = Relationship(back_populates="measures")
    document_id: int | None = Field(default=None, foreign_key="document.id")
    document: "Document" = Relationship(back_populates="measures")


class AbstractRequirementInput(SQLModel):
    reference: str | None
    summary: str
    description: str | None


class RequirementInput(AbstractRequirementInput):
    target_object: str | None
    compliance_status: constr(regex=r"^(C|PC|NC|N/A)$") | None
    compliance_comment: str | None

    @validator("compliance_comment")
    def compliance_comment_validator(cls, v, values):
        if (
            v
            and ("compliance_status" in values)
            and (values["compliance_status"] is None)
        ):
            raise ValueError(
                "compliance_comment cannot be set if compliance_status is None"
            )
        return v


class Requirement(RequirementInput, CommonFieldsMixin, table=True):
    project_id: int | None = Field(default=None, foreign_key="project.id")
    project: "Project" = Relationship(
        back_populates="requirements", sa_relationship_kwargs=dict(lazy="joined")
    )
    catalog_requirement_id: int | None = Field(
        default=None, foreign_key="catalog_requirement.id"
    )
    catalog_requirement: "CatalogRequirement" = Relationship(
        back_populates="requirements", sa_relationship_kwargs=dict(lazy="joined")
    )
    measures: list[Measure] = Relationship(
        back_populates="requirement",
        sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
    )

    @property
    def completion(self) -> float | None:
        if self.compliance_status not in ("C", "PC", None):
            return None

        session = Session.object_session(self)

        # get the total number of measures subordinated to this requirement
        total_query = (
            select([func.count()])
            .select_from(Measure)
            .where(Measure.requirement_id == self.id)
        )
        total = session.execute(total_query).scalar()

        # get the number of completed measures subordinated to this requirement
        completed_query = total_query.where(Measure.completed == True)
        completed = session.execute(completed_query).scalar()

        return completed / total if total else 0.0


class CatalogRequirementInput(AbstractRequirementInput):
    # Special fields for IT Grundschutz Kompendium
    gs_anforderung_reference: str | None
    gs_absicherung: constr(regex=r"^(B|S|H)$") | None
    gs_verantwortliche: str | None


class CatalogRequirement(CatalogRequirementInput, CommonFieldsMixin, table=True):
    __tablename__ = "catalog_requirement"
    catalog_module_id: int | None = Field(default=None, foreign_key="catalog_module.id")
    catalog_module: "CatalogModule" = Relationship(
        back_populates="catalog_requirements",
        sa_relationship_kwargs=dict(lazy="joined"),
    )
    requirements: list[Requirement] = Relationship(back_populates="catalog_requirement")


class CatalogModuleInput(SQLModel):
    reference: str | None
    title: str
    description: str | None

    # Special fields for IT Grundschutz Kompendium
    gs_reference: str | None


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
    project: "Project" = Relationship(back_populates="documents")
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
    _jira_project: JiraProject = PrivateAttr()

    @property
    def jira_project(self) -> JiraProject | None:
        if self.jira_project_id is None:
            return None

        get_jira_project: Callable | None = getattr(self, "_get_jira_project", None)
        jira_project: JiraProject | None = getattr(self, "_jira_project", None)
        if jira_project is None or jira_project.id != self.jira_project_id:
            if get_jira_project is None:
                raise RuntimeError("get_jira_project not set")
            jira_project = get_jira_project(self.jira_project_id)
            self._jira_project = jira_project

        return jira_project

    @property
    def completion(self) -> float | None:
        session = Session.object_session(self)

        # get the total number of measures in project
        total_query = (
            select([func.count()])
            .select_from(Measure, Requirement)
            .outerjoin(Measure)
            .where(
                Requirement.project_id == self.id,
                or_(
                    Requirement.compliance_status.in_(("C", "PC")),
                    Requirement.compliance_status.is_(None),
                ),
            )
        )
        total = session.execute(total_query).scalar()

        # get the number of completed measures in project
        completed_query = total_query.where(Measure.completed == True)
        completed = session.execute(completed_query).scalar()

        return completed / total if total else None


class CatalogOutput(CatalogInput):
    id: int


class CatalogModuleOutput(CatalogModuleInput):
    id: int
    catalog: CatalogOutput


class ProjectOutput(ProjectInput):
    id: int
    jira_project: JiraProject | None
    completion: confloat(ge=0, le=1) | None


class DocumentOutput(DocumentInput):
    id: int
    project: ProjectOutput


class CatalogRequirementOutput(CatalogRequirementInput):
    id: int
    catalog_module: CatalogModuleOutput

    # Special fields for IT Grundschutz Kompendium
    gs_anforderung_reference: str | None
    gs_absicherung: constr(regex=r"^(B|S|H)$") | None
    gs_verantwortliche: str | None


class RequirementOutput(RequirementInput):
    id: int
    project: ProjectOutput
    catalog_requirement: CatalogRequirementOutput | None
    completion: confloat(ge=0, le=1) | None


class MeasureOutput(SQLModel):
    id: int
    summary: str
    description: str | None
    completed: bool = False
    requirement: RequirementOutput
    jira_issue_id: str | None
    jira_issue: JiraIssue | None
    document: DocumentOutput | None
