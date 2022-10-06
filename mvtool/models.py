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
from pydantic import confloat, constr, validator
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


class RequirementInput(SQLModel):
    reference: str | None
    summary: str
    description: str | None
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
    project: "Project" = Relationship(back_populates="requirements")
    measures: list[Measure] = Relationship(
        back_populates="requirement",
        sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
    )

    # Special fields for IT Grundschutz Kompendium
    gs_anforderung_reference: str | None
    gs_absicherung: constr(regex=r"^(B|S|H)$") | None
    gs_verantwortliche: str | None
    catalog_module_id: int | None = Field(default=None, foreign_key="catalog_module.id")
    catalog_module: "CatalogModule" = Relationship(
        back_populates="requirements", sa_relationship_kwargs={"cascade": "all,delete"}
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


class CatalogModuleInput(SQLModel):
    reference: str
    title: str
    description: str | None

    # Special fields for IT Grundschutz Kompendium
    gs_reference: str | None


class CatalogModule(CatalogModuleInput, CommonFieldsMixin, table=True):
    __tablename__ = "catalog_module"
    requirements: list[Requirement] = Relationship(back_populates="catalog_module")


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


class ProjectOutput(ProjectInput):
    id: int
    jira_project: JiraProject | None
    completion: confloat(ge=0, le=1) | None


class DocumentOutput(DocumentInput):
    id: int
    project: ProjectOutput


class RequirementOutput(RequirementInput):
    id: int
    project: ProjectOutput
    completion: confloat(ge=0, le=1) | None

    # Special fields for IT Grundschutz Kompendium
    gs_anforderung_reference: str | None
    gs_absicherung: constr(regex=r"^(B|S|H)$") | None
    gs_verantwortliche: str | None
    catalog_module: CatalogModule | None


class MeasureOutput(SQLModel):
    id: int
    summary: str
    description: str | None
    completed: bool = False
    requirement: RequirementOutput
    jira_issue_id: str | None
    jira_issue: JiraIssue | None
    document: DocumentOutput | None
