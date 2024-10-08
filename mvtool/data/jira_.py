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

from typing import Annotated, Iterator

from fastapi import Depends
from jira import JIRA, JIRAError
from jira.resources import Issue, IssueType, Project, Resource, Status, User
from pydantic import Field

from ..auth import get_jira
from ..models import (
    JiraIssue,
    JiraIssueInput,
    JiraIssueStatus,
    JiraIssueType,
    JiraProject,
    JiraUser,
)


class JiraBase:
    def __init__(self, jira: JIRA = Depends(get_jira)):
        self.jira = jira

    def _get_jira_item_url(self, item_key: str) -> str:
        """Generates URL for JIRA project or issue."""
        return f"{self.jira.server_url}/browse/{item_key}"

    @staticmethod
    def _to_jira_user_model(data: dict | User) -> JiraUser:
        # Checking for Resource is more robust than checking for User
        data = data.raw if isinstance(data, Resource) else data
        return JiraUser(
            # JIRA user id is either "name" or "accountId" depending on JIRA server or cloud
            id=data.get("name") or data["accountId"],
            display_name=data["displayName"],
            email_address=data["emailAddress"],
        )

    def _to_jira_project_model(self, data: Project) -> JiraProject:
        return JiraProject(
            id=data.id,
            name=data.name,
            key=data.key,
            url=self._get_jira_item_url(data.key),
        )

    @staticmethod
    def _to_jira_issue_type_model(data: IssueType) -> JiraIssueType:
        return JiraIssueType(
            id=data.id,
            name=data.name,
        )

    @staticmethod
    def _to_jira_issue_status_model(data: Status) -> JiraIssueStatus:
        return JiraIssueStatus(
            name=data.name,
            color_name=data.statusCategory.colorName,
            completed=data.statusCategory.colorName.lower() == "green",
        )

    def _to_jira_issue_model(self, data: Issue) -> JiraIssue:
        return JiraIssue(
            id=data.id,
            key=data.key,
            summary=data.fields.summary,
            description=data.fields.description,
            assignee=(
                self._to_jira_user_model(data.fields.assignee)
                if data.fields.assignee
                else None
            ),
            issuetype=self._to_jira_issue_type_model(data.fields.issuetype),
            project=self._to_jira_project_model(data.fields.project),
            status=self._to_jira_issue_status_model(data.fields.status),
            url=self._get_jira_item_url(data.key),
        )

    def _from_jira_issue_input(
        self, input: JiraIssueInput, jira_project_id: str | None = None
    ) -> dict:
        """Converts JiraIssueInput to dict for creating or updating a JIRA issue."""

        # First handle the non-optional fields of JiraIssueInput
        data = dict(
            summary=input.summary,
            description=input.description,
            issuetype=dict(id=input.issuetype_id),
        )

        # Handle the optional project ID which is needed for creating a new issue
        if jira_project_id is not None:
            data["project"] = dict(id=jira_project_id)

        # Handle the optional assignee ID
        if input.assignee_id is not None:
            # Define assignee_dict depending on JIRA server or cloud
            key = "accountId" if self.jira._is_cloud else "name"
            data["assignee"] = {key: input.assignee_id}
        elif "assignee_id" in input.model_fields_set:
            data["assignee"] = None

        return data


class JiraUsers(JiraBase):
    def search_jira_users(
        self,
        search_str: str,
        jira_project_key: str,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Iterator[JiraUser]:
        jira_users_data = self.jira.search_assignable_users_for_issues(
            project=jira_project_key,  # use JIRA project key to be compatible with JIRA server
            startAt=offset or 0,
            maxResults=limit or 0,
            query=search_str,
            username=search_str,
        )

        for jira_user_data in jira_users_data:
            # TODO: add caching for JIRA users
            yield self._to_jira_user_model(jira_user_data.raw)

    def get_jira_user(self, jira_user_id: str | None = None) -> JiraUser:
        if jira_user_id is not None:
            jira_user_data = self.jira.user(jira_user_id)
        else:
            jira_user_data = self.jira.myself()
        return self._to_jira_user_model(jira_user_data)


class JiraProjects(JiraBase):
    def __init__(self, jira: JIRA = Depends(get_jira)):
        super().__init__(jira)
        self._jira_projects_cache = {}

    def _cache_jira_project(self, jira_project: JiraProject) -> None:
        self._jira_projects_cache[jira_project.id] = jira_project

    def lookup_jira_project(
        self, jira_project_id: str | None, try_to_get: bool = True
    ) -> JiraProject | None:
        """Returns JIRA project from cache or tries to get it from JIRA."""
        try:
            return self._jira_projects_cache[jira_project_id]
        except KeyError:
            if try_to_get:
                jira_project = self.try_to_get_jira_project(jira_project_id)
                self._jira_projects_cache[jira_project_id] = jira_project
                return jira_project
            else:
                return None

    def list_jira_projects(self) -> Iterator[JiraProject]:
        for jira_project_data in self.jira.projects():
            jira_project = self._to_jira_project_model(jira_project_data)
            self._cache_jira_project(jira_project)
            yield jira_project

    def get_jira_project(self, jira_project_id: str) -> JiraProject:
        jira_project = self._to_jira_project_model(self.jira.project(jira_project_id))
        self._cache_jira_project(jira_project)
        return jira_project

    def check_jira_project_id(self, jira_project_id: str | None) -> JiraProject | None:
        """Raises an Exception if project ID is not existing or not None."""
        if jira_project_id is not None:
            return self.get_jira_project(jira_project_id)

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


class JiraIssueTypes(JiraBase):
    def list_jira_issue_types(self, jira_project_id: str):
        for issue_type_data in self.jira.project(jira_project_id).issueTypes:
            yield self._to_jira_issue_type_model(issue_type_data)


class JiraIssues(JiraBase):
    def __init__(self, jira: JIRA = Depends(get_jira)):
        super().__init__(jira)
        self._jira_issues_cache = {}

    def _cache_jira_issue(self, jira_issue: JiraIssue) -> None:
        self._jira_issues_cache[jira_issue.id] = jira_issue

    def uncache_jira_issue(self, jira_issue_id: str) -> None:
        try:
            del self._jira_issues_cache[jira_issue_id]
        except KeyError:
            pass

    def lookup_jira_issue(
        self, jira_issue_id: str | None, try_to_get: bool = False
    ) -> JiraIssue | None:
        """Returns JIRA issue from cache or tries to get it from JIRA."""
        try:
            return self._jira_issues_cache[jira_issue_id]
        except KeyError:
            if try_to_get:
                jira_issue = self.try_to_get_jira_issue(jira_issue_id)
                self._jira_issues_cache[jira_issue_id] = jira_issue
                return jira_issue
            else:
                return None

    def list_jira_issues(
        self,
        jql_str: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Iterator[JiraIssue]:
        jira_issues_data = self.jira.search_issues(
            jql_str or "",
            startAt=offset or 0,
            maxResults=limit or 0,
            validate_query=False,  # Turn off validation of JQL queries
        )

        for jira_issue_data in jira_issues_data:
            jira_issue = self._to_jira_issue_model(jira_issue_data)
            self._cache_jira_issue(jira_issue)
            yield jira_issue

    def count_jira_issues(self, jql_str: str | None = None) -> int:
        return self.jira.search_issues(
            jql_str or "",
            maxResults=1,  # Query only one issue to get the total count, 0 queries all
            validate_query=False,
        ).total

    def create_jira_issue(
        self, jira_project_id: str, jira_issue_input: JiraIssueInput
    ) -> JiraIssue:
        jira_issue = self._to_jira_issue_model(
            self.jira.create_issue(
                self._from_jira_issue_input(jira_issue_input, jira_project_id)
            )
        )
        self._cache_jira_issue(jira_issue)
        return jira_issue

    def get_jira_issue(self, jira_issue_id: str):
        jira_issue = self._to_jira_issue_model(self.jira.issue(jira_issue_id))
        self._cache_jira_issue(jira_issue)
        return jira_issue

    def update_jira_issue(self, jira_issue_id: str, jira_issue_input: JiraIssueInput):
        jira_issue_data = self.jira.issue(jira_issue_id)
        jira_issue_data.update(**self._from_jira_issue_input(jira_issue_input))
        jira_issue = self._to_jira_issue_model(jira_issue_data)
        self._cache_jira_issue(jira_issue)
        return jira_issue

    def delete_jira_issue(self, jira_issue_id: str):
        jira_issue_data = self.jira.issue(jira_issue_id)
        jira_issue_data.delete()
        self.uncache_jira_issue(jira_issue_id)

    def get_jira_issues(
        self,
        jira_issue_ids: tuple[str],
        offset: Annotated[int, Field(ge=0)] = 0,
        size: Annotated[int, Field(ge=0)] | None = None,
    ) -> Iterator[JiraIssue]:
        jql_str = " OR ".join(f"id = {id}" for id in jira_issue_ids)
        return self.list_jira_issues(jql_str, offset, size) if jql_str else []

    def check_jira_issue_id(self, jira_issue_id: str | None) -> JiraIssue | None:
        """Raises an Exception if issue ID is not existing or not None."""
        if jira_issue_id is not None:
            return self.get_jira_issue(jira_issue_id)

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
