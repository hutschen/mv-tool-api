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


from jira import JIRA, Issue, Project, JIRAError
from pydantic import conint
from fastapi import Depends, APIRouter, Response
from fastapi_utils.cbv import cbv

from ..auth import get_jira
from ..models import (
    JiraProject,
    JiraIssueType,
    JiraIssueStatus,
    JiraIssueInput,
    JiraIssue,
    JiraUser,
)

router = APIRouter()


class JiraBaseView:
    def __init__(self, jira: JIRA = Depends(get_jira)):
        self.jira = jira

    def _get_jira_item_url(self, item_key: str) -> str:
        """Generates URL for JIRA project or issue."""
        return f"{self.jira.server_url}/browse/{item_key}"


@cbv(router)
class JiraUserView(JiraBaseView):
    kwargs = dict(tags=["jira-user"])

    @router.get("/jira-user", response_model=JiraUser, **kwargs)
    def get_jira_user(self):
        myself_data = self.jira.myself()
        return JiraUser(
            display_name=myself_data["displayName"],
            email_address=myself_data["emailAddress"],
        )


@cbv(router)
class JiraProjectsView(JiraBaseView):
    kwargs = dict(tags=["jira-project"])

    def _convert_to_jira_project(self, jira_project_data: Project) -> JiraProject:
        return JiraProject(
            id=jira_project_data.id,
            name=jira_project_data.name,
            key=jira_project_data.key,
            url=self._get_jira_item_url(jira_project_data.key),
        )

    @router.get("/jira-projects", response_model=list[JiraProject], **kwargs)
    def list_jira_projects(self):
        for jira_project_data in self.jira.projects():
            yield self._convert_to_jira_project(jira_project_data)

    @router.get(
        "/jira-projects/{jira_project_id}", response_model=JiraProject, **kwargs
    )
    def get_jira_project(self, jira_project_id: str) -> JiraProject:
        jira_project_data = self.jira.project(jira_project_id)
        return self._convert_to_jira_project(jira_project_data)

    def check_jira_project_id(self, jira_project_id: str | None) -> None:
        """Raises an Exception if project ID is not existing or not None."""
        if jira_project_id is not None:
            self.get_jira_project(jira_project_id)

    def try_to_get_jira_project(self, jira_project_id: str) -> JiraProject | None:
        """Returns JIRA project if it exists. If not, None is returned.

        None can mean that the project does not exist or the logged in JIRA
        user has no access rights for the project.
        """
        if jira_project_id is not None:
            try:
                return self.get_jira_project(jira_project_id)
            except JIRAError as error:
                if error.status_code != 404:
                    raise error


@cbv(router)
class JiraIssueTypesView(JiraBaseView):
    kwargs = dict(tags=["jira-issue-type"])

    @router.get(
        "/jira-projects/{jira_project_id}/jira-issuetypes",
        response_model=list[JiraIssueType],
        **kwargs,
    )
    def list_jira_issue_types(self, jira_project_id: str):
        for issue_type_data in self.jira.project(jira_project_id).issueTypes:
            yield JiraIssueType.from_orm(issue_type_data)


@cbv(router)
class JiraIssuesView(JiraBaseView):
    kwargs = dict(tags=["jira-issues"])

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
                color_name=jira_issue_data.fields.status.statusCategory.colorName,
                completed=jira_issue_data.fields.status.statusCategory.colorName.lower()
                == "green",
            ),
            url=self._get_jira_item_url(jira_issue_data.key),
        )

    @router.get(
        "/jira-projects/{jira_project_id}/jira-issues",
        response_model=list[JiraIssue],
        **kwargs,
    )
    def list_jira_issues(
        self,
        jira_project_id: str,
        offset: conint(ge=0) = 0,
        size: conint(ge=0) | None = None,
    ) -> list[JiraIssue]:
        jira_query = f"project = {jira_project_id}"
        jira_issues_data = self.jira.search_issues(
            jira_query, startAt=offset, maxResults=size
        )
        return [self._convert_to_jira_issue(d) for d in jira_issues_data]

    @router.post(
        "/jira-projects/{jira_project_id}/jira-issues",
        status_code=201,
        response_model=JiraIssue,
        **kwargs,
    )
    def create_jira_issue(
        self, jira_project_id: str, jira_issue_input: JiraIssueInput
    ) -> JiraIssue:
        jira_issue_data = self.jira.create_issue(
            dict(
                summary=jira_issue_input.summary,
                description=jira_issue_input.description,
                project=dict(id=jira_project_id),
                issuetype=dict(id=jira_issue_input.issuetype_id),
            )
        )
        return self._convert_to_jira_issue(jira_issue_data)

    @router.get("/jira-issues/{jira_issue_id}", response_model=JiraIssue, **kwargs)
    def get_jira_issue(self, jira_issue_id: str):
        jira_issue_data = self.jira.issue(id=jira_issue_id)
        return self._convert_to_jira_issue(jira_issue_data)

    @router.put("/jira-issues/{jira_issue_id}", response_model=JiraIssue, **kwargs)
    def update_jira_issue(self, jira_issue_id: str, jira_issue_input: JiraIssueInput):
        jira_issue_data = self.jira.issue(id=jira_issue_id)
        jira_issue_data.update(
            summary=jira_issue_input.summary,
            description=jira_issue_input.description,
            issuetype=dict(id=jira_issue_input.issuetype_id),
        )
        return self._convert_to_jira_issue(jira_issue_data)

    @router.delete(
        "/jira-issues/{jira_issue_id}",
        status_code=204,
        response_class=Response,
        **kwargs,
    )
    def delete_jira_issue(self, jira_issue_id: str):
        jira_issue_data = self.jira.issue(id=jira_issue_id)
        jira_issue_data.delete()

    def get_jira_issues(
        self,
        jira_issue_ids: tuple[str],
        offset: conint(ge=0) = 0,
        size: conint(ge=0) | None = None,
    ) -> list[JiraIssue]:
        if not jira_issue_ids:
            return []

        jira_query = " OR ".join(f"id = {id}" for id in jira_issue_ids)
        jira_issues_data = self.jira.search_issues(
            jira_query, validate_query=False, startAt=offset, maxResults=size
        )
        return [self._convert_to_jira_issue(d) for d in jira_issues_data]

    def check_jira_issue_id(self, jira_issue_id: str | None) -> None:
        """Raises an Exception if issue ID is not existing or not None."""
        if jira_issue_id is not None:
            self.get_jira_issue(jira_issue_id)

    def try_to_get_jira_issue(self, jira_issue_id: str) -> JiraIssue | None:
        """Returns JIRA issue if it exists. If not, None is returned.

        None can mean that the issue does not exist or the logged in JIRA
        user has no access rights for the issue.
        """
        if jira_issue_id is not None:
            try:
                return self.get_jira_issue(jira_issue_id)
            except JIRAError as error:
                if error.status_code != 404:
                    raise error
