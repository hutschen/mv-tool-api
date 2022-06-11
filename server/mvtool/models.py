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

from sqlalchemy import table
from sqlmodel import SQLModel, Field, Relationship


class JiraProject(SQLModel):
    id: str
    key: str
    name: str


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
    description: str | None
    

class Measure(MeasureInput, table=True):
    id: int | None = Field(default=None, primary_key=True)
    requirement_id: int | None = Field(default=None, foreign_key='requirement.id')
    requirement : 'Requirement' = Relationship(back_populates='measures')  


class RequirementInput(SQLModel):
    reference: str | None
    summary: str
    description: str | None
    target_object: str | None
    compliance_status: str | None
    compliance_comment: str | None


class Requirement(RequirementInput, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int | None = Field(default=None, foreign_key='project.id')
    project: 'Project' = Relationship(back_populates='requirements')
    measures: list[Measure] = Relationship(back_populates='requirement')


class ProjectInput(SQLModel):
    name: str
    description: str | None = None
    jira_project_id: str | None = None


class Project(ProjectInput, table=True):
    id: int | None = Field(default=None, primary_key=True)
    requirements: list[Requirement] = Relationship(back_populates='project')