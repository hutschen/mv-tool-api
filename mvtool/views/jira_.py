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

from jira import JIRA, Issue, JIRAError
from pydantic import conint
from fastapi import Depends, APIRouter
from fastapi_utils.cbv import cbv
from ..auth import get_jira
from ..models import (JiraProject, JiraIssueType, JiraIssueStatus, 
    JiraIssueInput, JiraIssue, JiraUser)

router = APIRouter()

class JiraBaseView:
    def __init__(self, jira: JIRA = Depends(get_jira)):
        self.jira = jira


@cbv(router)
class JiraUserView(JiraBaseView):
    kwargs = dict(tags=['jira-user'])

    @router.get('/user', response_model=JiraUser, **kwargs)
    def get_jira_user(self):
        myself_data = self.jira.myself()
        return JiraUser(
            display_name=myself_data['displayName'],
            email_address=myself_data['emailAddress'])


@cbv(router)
class JiraProjectsView(JiraBaseView):
    kwargs = dict(tags=['jira-project'])

    @router.get('/projects', response_model=list[JiraProject], **kwargs)
    def list_jira_projects(self):
        for jira_project_data in self.jira.projects():
            yield JiraProject.from_orm(jira_project_data)

    @router.get(
        '/projects/{jira_project_id}', response_model=JiraProject, **kwargs)
    def get_jira_project(self, jira_project_id: str) -> JiraProject:
        jira_project_data = self.jira.project(jira_project_id)
        return JiraProject.from_orm(jira_project_data)

    def check_jira_project_id(self, jira_project_id: str | None) -> None:
        ''' Raises an Exception if project ID is not existing or not None.
        '''
        if jira_project_id is not None:
            self.get_jira_project(jira_project_id)

    def try_to_get_jira_project(
            self, jira_project_id: str) -> JiraProject | None:
        ''' Returns JIRA project if it exists. If not, None is returned.

            None can mean that the project does not exist or the logged in JIRA 
            user has no access rights for the project.
        '''
        if jira_project_id is not None:
            try:
                return self.get_jira_project(jira_project_id)
            except JIRAError as error:
                if error.status_code != 404:
                    raise error
        

@cbv(router)
class JiraIssueTypesView(JiraBaseView):
    kwargs = dict(tags=['jira-issue-type'])

    @router.get(
        '/projects/{jira_project_id}/issuetypes',
        response_model=list[JiraIssueType], **kwargs)
    def list_jira_issue_types(self, jira_project_id: str):
        for issue_type_data in self.jira.project(jira_project_id).issueTypes:
            yield JiraIssueType.from_orm(issue_type_data)


@cbv(router)
class JiraIssuesView(JiraBaseView):
    kwargs = dict(tags=['jira-issues'])

    def _convert_to_jira_issue(self, jira_issue_data: Issue) -> JiraIssue:
        return JiraIssue(
            id=jira_issue_data.id,
            key=jira_issue_data.key,
            summary=jira_issue_data.fields.summary,
            description=jira_issue_data.fields.description,
            issuetype_id=jira_issue_data.fields.issuetype.id,
            project_id=jira_issue_data.fields.project.id,
            status=JiraIssueStatus(
                name=jira_issue_data.fields.status.name,
                color_name=jira_issue_data.fields.status.statusCategory.colorName
            )
        )

    @router.get(
        '/projects/{jira_project_id}/issues', response_model=list[JiraIssue],
        **kwargs)
    def list_jira_issues(
            self, jira_project_id: str, offset: conint(ge=0) = 0, 
            size: conint(ge=0) | None = None) -> list[JiraIssue]:
        jira_issues_data = self.jira.search_issues(
            f'project = {jira_project_id}', startAt=offset, maxResults=size)
        return [self._convert_to_jira_issue(d) for d in jira_issues_data]

    @router.post(
        '/projects/{jira_project_id}/issues', status_code=201, 
        response_model=JiraIssue, **kwargs)
    def create_jira_issue(
            self, jira_project_id: str, 
            jira_issue: JiraIssueInput) -> JiraIssue:
        jira_issue_data = self.jira.create_issue(dict(
            summary=jira_issue.summary,
            description=jira_issue.description,
            project=dict(id=jira_project_id),
            issuetype=dict(id=jira_issue.issuetype_id)
        ))
        return self._convert_to_jira_issue(jira_issue_data)

    @router.get('/issues/{jira_issue_id}', response_model=JiraIssue, **kwargs)
    def get_jira_issue(self, jira_issue_id: str):
        jira_issue_data = self.jira.issue(id=jira_issue_id)
        return self._convert_to_jira_issue(jira_issue_data)