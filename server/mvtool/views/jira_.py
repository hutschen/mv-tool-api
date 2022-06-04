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
from fastapi_utils.cbv import cbv
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
    issue_type_id: str
    project_id: str


class JiraIssue(JiraIssueInput, orm_mode=True):
    id: str


@cbv(router)
class JiraProjectsView:
    kwargs = dict(tags=['jira-project'])

    def __init__(self, jira: JIRA = Depends(get_jira)):
        self.jira = jira

    @router.get('/projects', response_model=list[JiraProject], **kwargs)
    def list_projects(self):
        for jira_project in self.jira.projects():
            yield JiraProject.from_orm(jira_project)

    @router.get('/projects/{project_id}', response_model=JiraProject, **kwargs)
    def get_project(self, project_id: str):
        jira_project = self.jira.project(project_id)
        return JiraProject.from_orm(jira_project)


@cbv(router)
class JiraIssueTypesView:
    def __init__(self, jira: JIRA = Depends(get_jira)):
        self.jira = jira

    @router.get(
        '/projects/{project_id}/issuetypes', 
        response_model=list[JiraIssueType], tags=['jira-issue-type'])
    def list_issue_types(self, project_id: str):
        for issue_type in self.jira.project(project_id).issueTypes:
            yield JiraIssueType.from_orm(issue_type)


@cbv(router)
class JiraIssueView:
    def __init__(self, jira: JIRA = Depends(get_jira)):
        self.jira = jira

    @router.post(
        '/issues', status_code=201, response_model=JiraIssue, 
        tags=['jira-issues'])
    def create_issue(self, new_issue: JiraIssueInput) -> JiraIssue:
        issue_data = new_issue.dict()
        issue_data['project'] = dict(id=new_issue.project_id)
        issue_data['issuetype'] = dict(id=new_issue.issue_type_id)
        del issue_data['project_id']
        del issue_data['issue_type_id']
        jira_issue = self.jira.create_issue(issue_data)

        new_issue = JiraIssue.from_orm(new_issue)
        new_issue.id = jira_issue.id
        return new_issue

    @router.get('/issues/{issue_id}', response_model=JiraIssue)
    def get_issue(self, issue_id: str):
        pass