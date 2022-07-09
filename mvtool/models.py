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

from pydantic import constr, validator
from sqlmodel import SQLModel, Field, Relationship


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


class JiraIssueInput(SQLModel):
    summary: str
    description: str | None = None
    issuetype_id: str


class JiraIssue(JiraIssueInput):
    id: str
    key: str
    project_id: str
    status: JiraIssueStatus


class MeasureInput(SQLModel):
    summary: str
    description: str | None = None
    completed: bool = False
    jira_issue_id: str | None = None
    document_id: int | None = None
    

class Measure(MeasureInput, table=True):
    id: int | None = Field(default=None, primary_key=True)
    requirement_id: int | None = Field(default=None, foreign_key='requirement.id')
    requirement : 'Requirement' = Relationship(back_populates='measures')  
    document_id: int | None = Field(default=None, foreign_key='document.id')
    document: 'Document' = Relationship(back_populates='measures')


class RequirementInput(SQLModel):
    reference: str | None
    summary: str
    description: str | None
    target_object: str | None
    compliance_status: constr(regex=r'^(C|PC|NC|N/A)$') | None
    compliance_comment: str | None

    @validator('compliance_comment')
    def compliance_comment_validator(cls, v, values):
        if values['compliance_status'] is None and v:
            raise ValueError(
                'compliance_comment cannot be set if compliance_status is None')
        return v


class Requirement(RequirementInput, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int | None = Field(default=None, foreign_key='project.id')
    project: 'Project' = Relationship(back_populates='requirements')
    measures: list[Measure] = Relationship(back_populates='requirement')


class DocumentInput(SQLModel):
    reference: str | None = None
    title: str
    description: str | None = None


class Document(DocumentInput, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int | None = Field(default=None, foreign_key='project.id')
    project: 'Project' = Relationship(back_populates='documents')
    measures: list[Measure] = Relationship(back_populates='document')


class ProjectInput(SQLModel):
    name: str
    description: str | None = None
    jira_project_id: str | None = None


class Project(ProjectInput, table=True):
    id: int | None = Field(default=None, primary_key=True)
    requirements: list[Requirement] = Relationship(back_populates='project')
    documents: list[Document] = Relationship(back_populates='project')


class ProjectOutput(ProjectInput):
    id: int
    jira_project: JiraProject | None = None


class DocumentOutput(DocumentInput):
    id: int
    project: Project


class RequirementOutput(RequirementInput):
    id: int
    project: Project


class MeasureOutput(SQLModel):
    id: int
    summary: str
    description: str | None = None
    completed: bool = False
    requirement: RequirementOutput
    jira_issue_id: str | None
    jira_issue: JiraIssue | None
    document: DocumentOutput | None