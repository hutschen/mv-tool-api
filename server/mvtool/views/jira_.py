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

from jira import JIRA, Issue
import jira
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


class JiraIssueStatus(BaseModel):
    name: str
    color_name: str


class JiraIssueInput(BaseModel):
    summary: str
    description: str | None = None
    issuetype_id: str


class JiraIssue(JiraIssueInput, orm_mode=True):
    id: str
    key: str
    project_id: str
    status: JiraIssueStatus


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

    def check_project_id(self, project_id: str | None) -> None:
        ''' Raises an Exception if project ID is not existing or not None.
        '''
        if project_id is not None:
            self.get_project(project_id)
        

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
        '/projects/{project_id}/issues', status_code=201, response_model=JiraIssue, 
        tags=['jira-issues'])
    def create_issue(self, project_id: str, new_issue: JiraIssueInput) -> JiraIssue:
        issue_data = new_issue.dict()
        issue_data['project'] = dict(id=project_id)
        issue_data['issuetype'] = dict(id=new_issue.issuetype_id)
        del issue_data['issuetype_id']
        jira_issue = self.jira.create_issue(issue_data)

        return JiraIssue(
            id=jira_issue.id,
            key=jira_issue.key,
            summary=jira_issue.fields.summary,
            description=jira_issue.fields.description,
            issuetype_id=jira_issue.fields.issuetype.id,
            project_id=jira_issue.fields.project.id,
            status=JiraIssueStatus(
                name=jira_issue.fields.status.name,
                color_name=jira_issue.fields.status.statusCategory.colorName
            )
        )

    @router.get('/issues/{issue_id}', response_model=JiraIssue)
    def get_issue(self, issue_id: str):
        pass