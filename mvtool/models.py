# coding: utf-8
#
# Copyright 2022 Helmar Hutschenreuter
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation. You may obtain
# a copy of the GNU AGPL V3 at https://www.gnu.org/licenses/.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AGPL V3 for more details.

from pydantic import confloat, constr, validator
from sqlmodel import SQLModel, Field, Relationship, Session, select, func, or_


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
    description: str | None = None
    issuetype_id: str


class JiraIssue(JiraIssueInput):
    id: str
    key: str
    project_id: str
    status: JiraIssueStatus
    url: str


class MeasureInput(SQLModel):
    summary: str
    description: str | None = None
    completed: bool = False
    document_id: int | None = None


class Measure(MeasureInput, table=True):
    id: int | None = Field(default=None, primary_key=True)
    jira_issue_id: str | None = None
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


class Requirement(RequirementInput, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int | None = Field(default=None, foreign_key="project.id")
    project: "Project" = Relationship(back_populates="requirements")
    measures: list[Measure] = Relationship(
        back_populates="requirement",
        sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
    )

    @property
    def completion(self) -> float:
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


class DocumentInput(SQLModel):
    reference: str | None = None
    title: str
    description: str | None = None


class Document(DocumentInput, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int | None = Field(default=None, foreign_key="project.id")
    project: "Project" = Relationship(back_populates="documents")
    measures: list[Measure] = Relationship(back_populates="document")


class ProjectInput(SQLModel):
    name: str
    description: str | None = None
    jira_project_id: str | None = None


class Project(ProjectInput, table=True):
    id: int | None = Field(default=None, primary_key=True)
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
    jira_project: JiraProject | None = None
    completion: confloat(ge=0, le=1) | None


class DocumentOutput(DocumentInput):
    id: int
    project: ProjectOutput


class RequirementOutput(RequirementInput):
    id: int
    project: ProjectOutput
    completion: confloat(ge=0, le=1)


class MeasureOutput(SQLModel):
    id: int
    summary: str
    description: str | None = None
    completed: bool = False
    requirement: RequirementOutput
    jira_issue_id: str | None
    jira_issue: JiraIssue | None
    document: DocumentOutput | None
