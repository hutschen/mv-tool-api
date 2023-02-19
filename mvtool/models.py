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


class AbstractComplianceInput(SQLModel):
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
                "compliance_comment cannot be set when compliance_status is None"
            )
        return v


class MeasureInput(AbstractComplianceInput):
    reference: str | None
    summary: str
    description: str | None
    completion_status: constr(regex=r"^(open|in progress|completed)$") | None
    completion_comment: str | None
    verified: bool = False
    verification_method: constr(regex=r"^(I|T|R)$") | None
    verification_comment: str | None
    document_id: int | None
    jira_issue_id: str | None

    @validator("completion_comment")
    def completion_comment_validator(cls, v, values):
        if (
            v
            and ("completion_status" in values)
            and (values["completion_status"] is None)
        ):
            raise ValueError(
                "completion_comment cannot be set when compliance_status is None"
            )
        return v


class Measure(MeasureInput, CommonFieldsMixin, table=True):
    requirement_id: int | None = Field(default=None, foreign_key="requirement.id")
    requirement: "Requirement" = Relationship(
        back_populates="measures", sa_relationship_kwargs=dict(lazy="joined")
    )
    document_id: int | None = Field(default=None, foreign_key="document.id")
    document: "Document" = Relationship(
        back_populates="measures", sa_relationship_kwargs=dict(lazy="joined")
    )

    _get_jira_issue: Callable = PrivateAttr()

    @property
    def jira_issue(self) -> JiraIssue | None:
        if self.jira_issue_id is None:
            return None

        return getattr(self, "_get_jira_issue")(self.jira_issue_id)

    @property
    def completion_status_hint(self):
        if self.compliance_status not in ("C", "PC", None):
            return None

        if self.jira_issue and self.jira_issue.status.completed:
            return "completed"
        else:
            return self.completion_status

    @property
    def verified_hint(self):
        if self.compliance_status not in ("C", "PC", None):
            return False

        if self.completion_status == "completed":
            return self.verified
        else:
            return False


class AbstractRequirementInput(SQLModel):
    reference: str | None
    summary: str
    description: str | None


class RequirementInput(AbstractRequirementInput, AbstractComplianceInput):
    catalog_requirement_id: int | None
    target_object: str | None
    milestone: str | None


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
    def compliance_status_hint(self):
        session = Session.object_session(self)

        # get the compliance states of all measures subordinated to this requirement
        compliance_query = select([Measure.compliance_status]).where(
            Measure.requirement_id == self.id, Measure.compliance_status != None
        )
        compliance_states = session.execute(compliance_query).scalars().all()

        # compute the compliance status hint
        exists = lambda x: any(x == c in compliance_states for c in compliance_states)
        every = lambda x: all(x == c for c in compliance_states)

        if exists("C") and not (exists("PC") or exists("NC")):
            return "C"
        elif exists("PC") or (exists("C") and exists("NC")):
            return "PC"
        elif exists("NC") and not (exists("C") or exists("PC")):
            return "NC"
        elif every("N/A") and len(compliance_states) > 0:
            return "N/A"
        else:
            return None

    @property
    def _compliant_count_query(self):
        return (
            select([func.count()])
            .select_from(Measure)
            .where(
                Measure.requirement_id == self.id,
                or_(
                    Measure.compliance_status.in_(("C", "PC")),
                    Measure.compliance_status.is_(None),
                ),
            )
        )

    @property
    def completion_progress(self) -> float | None:
        if self.compliance_status not in ("C", "PC", None):
            return None

        session = Session.object_session(self)

        # get the total number of measures subordinated to this requirement
        total = session.execute(self._compliant_count_query).scalar()

        # get the number of completed measures subordinated to this requirement
        completed_query = self._compliant_count_query.where(
            Measure.completion_status == "completed"
        )
        completed = session.execute(completed_query).scalar()

        return completed / total if total else 0.0

    @property
    def verification_progress(self) -> float | None:
        if self.compliance_status not in ("C", "PC", None):
            return None

        session = Session.object_session(self)

        # get the total number of measures subordinated to this requirement
        total = session.execute(self._compliant_count_query).scalar()

        # get the number of verified measures subordinated to this requirement
        verified_query = self._compliant_count_query.where(Measure.verified == True)
        verified = session.execute(verified_query).scalar()

        return verified / total if total else 0.0


class CatalogRequirementInput(AbstractRequirementInput):
    # Special fields for IT Grundschutz Kompendium
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
        verified_query = self._compliant_count_query.where(Measure.verified == True)
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


class CatalogRequirementRepresentation(SQLModel):
    id: int
    reference: str | None
    summary: str


class CatalogRequirementOutput(CatalogRequirementInput):
    id: int
    catalog_module: CatalogModuleOutput

    # Special fields for IT Grundschutz Kompendium
    gs_absicherung: constr(regex=r"^(B|S|H)$") | None
    gs_verantwortliche: str | None


class RequirementRepresentation(SQLModel):
    id: int
    reference: str | None
    summary: str


class RequirementOutput(AbstractRequirementInput):
    id: int
    project: ProjectOutput
    catalog_requirement: CatalogRequirementOutput | None
    target_object: str | None
    milestone: str | None
    compliance_status: str | None
    compliance_status_hint: str | None
    compliance_comment: str | None
    completion_progress: confloat(ge=0, le=1) | None
    verification_progress: confloat(ge=0, le=1) | None


class MeasureRepresentation(SQLModel):
    id: int
    reference: str | None
    summary: str


class MeasureOutput(MeasureRepresentation):
    description: str | None
    compliance_status: str | None
    compliance_comment: str | None
    completion_status: str | None
    completion_status_hint: str | None
    completion_comment: str | None
    verified: bool
    verified_hint: bool
    verification_method: str | None
    verification_comment: str | None
    requirement: RequirementOutput
    jira_issue_id: str | None
    jira_issue: JiraIssue | None
    document: DocumentOutput | None
