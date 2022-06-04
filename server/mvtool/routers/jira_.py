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

from jira import JIRA
from pydantic import BaseModel
from fastapi import Depends, APIRouter
from ..auth import get_jira

router = APIRouter()


class JiraProject(BaseModel, orm_mode=True):
    id: str
    key: str
    name: str


class JiraIssueType(BaseModel, orm_mode=True):
    id: str
    name: str


class JiraIssueInput(BaseModel):
    summary: str
    description: str | None = None


class JiraIssue(JiraIssueInput, orm_mode=True):
    id: str


@router.get('/projects', response_model=list[JiraProject])
def get_jira_projects(jira: JIRA = Depends(get_jira)):
    for p in jira.projects():
        yield JiraProject.from_orm(p)

@router.get('/projects/{project_id}', response_model=JiraProject)
def get_jira_project(
        project_id: str, jira: JIRA = Depends(get_jira)):
    p = jira.project(project_id)
    return JiraProject.from_orm(p)

@router.get(
    '/projects/{project_id}/issuetypes', response_model=list[JiraIssueType])
def get_issue_types(project_id: str, jira: JIRA = Depends(get_jira)):
    for it in jira.project(project_id).issueTypes:
        yield JiraIssueType.from_orm(it)

@router.post(
    '/projects/{project_id}/issues', status_code=201, response_model=dict)
def create_jira_issue(
        jira_issue_input: JiraIssueInput,
        project_id: str, issue_type_id: str, jira: JIRA = Depends(get_jira)):
    jira_issue_data = jira_issue_input.dict()
    jira_issue_data['project'] = dict(id=project_id)
    jira_issue_data['issuetype'] = dict(id=issue_type_id)
    i = jira.create_issue(jira_issue_data)
    return i.raw
    # print(i.raw)
    #jira_issue = JiraIssue(id=i.id, summary=i.summary, description=i.description)
    #return JiraIssue.from_orm(i)

@router.get('/issues/{issue_id}', response_model=JiraIssue)
def get_jira_issue(issue_id: str, jira: JIRA = Depends(get_jira)):
    pass