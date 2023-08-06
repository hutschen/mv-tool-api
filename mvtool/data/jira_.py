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


from typing import Iterator
from jira import JIRA, Issue, Project, JIRAError
from pydantic import conint
from fastapi import Depends

from ..auth import get_jira
from ..models import (
    JiraProject,
    JiraIssueType,
    JiraIssueStatus,
    JiraIssueInput,
    JiraIssue,
    JiraUser,
)


class JiraBase:
    def __init__(self, jira: JIRA = Depends(get_jira)):
        self.jira = jira

    def _get_jira_item_url(self, item_key: str) -> str:
        """Generates URL for JIRA project or issue."""
        return f"{self.jira.server_url}/browse/{item_key}"


class JiraUsers(JiraBase):
    def get_jira_user(self):
        myself_data = self.jira.myself()
        return JiraUser(
            display_name=myself_data["displayName"],
            email_address=myself_data["emailAddress"],
        )


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

    def _convert_to_jira_project(self, jira_project_data: Project) -> JiraProject:
        return JiraProject(
            id=jira_project_data.id,
            name=jira_project_data.name,
            key=jira_project_data.key,
            url=self._get_jira_item_url(jira_project_data.key),
        )

    def list_jira_projects(self) -> Iterator[JiraProject]:
        for jira_project_data in self.jira.projects():
            jira_project = self._convert_to_jira_project(jira_project_data)
            self._cache_jira_project(jira_project)
            yield jira_project

    def get_jira_project(self, jira_project_id: str) -> JiraProject:
        jira_project = self._convert_to_jira_project(self.jira.project(jira_project_id))
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
            yield JiraIssueType.model_validate(issue_type_data)


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
            jira_issue = self._convert_to_jira_issue(jira_issue_data)
            self._cache_jira_issue(jira_issue)
            yield jira_issue

    def count_jira_issues(self, jira_project_id: str) -> int:
        jira_query = f"project = {jira_project_id}"
        return self.jira.search_issues(jira_query, maxResults=0).total

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
        jira_issue = self._convert_to_jira_issue(jira_issue_data)
        self._cache_jira_issue(jira_issue)
        return jira_issue

    def get_jira_issue(self, jira_issue_id: str):
        jira_issue = self._convert_to_jira_issue(self.jira.issue(jira_issue_id))
        self._cache_jira_issue(jira_issue)
        return jira_issue

    def update_jira_issue(self, jira_issue_id: str, jira_issue_input: JiraIssueInput):
        jira_issue_data = self.jira.issue(jira_issue_id)
        jira_issue_data.update(
            summary=jira_issue_input.summary,
            description=jira_issue_input.description,
            issuetype=dict(id=jira_issue_input.issuetype_id),
        )
        jira_issue = self._convert_to_jira_issue(jira_issue_data)
        self._cache_jira_issue(jira_issue)
        return jira_issue

    def delete_jira_issue(self, jira_issue_id: str):
        jira_issue_data = self.jira.issue(jira_issue_id)
        jira_issue_data.delete()
        self.uncache_jira_issue(jira_issue_id)

    def get_jira_issues(
        self,
        jira_issue_ids: tuple[str],
        offset: conint(ge=0) = 0,
        size: conint(ge=0) | None = None,
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
