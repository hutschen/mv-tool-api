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

from fastapi import APIRouter, Depends, Response
from pydantic import conint

from ..data.jira_ import (
    JiraIssues,
    JiraIssueTypes,
    JiraProjects,
    JiraUsers,
)
from ..models import JiraIssue, JiraIssueInput, JiraIssueType, JiraProject, JiraUser

router = APIRouter()


@router.get("/jira-user", response_model=JiraUser, tags=["jira-user"])
def get_jira_user(jira_user_view: JiraUsers = Depends()):
    return jira_user_view.get_jira_user()


_kwargs_jira_projects = dict(tags=["jira-project"])


@router.get("/jira-projects", response_model=list[JiraProject], **_kwargs_jira_projects)
def get_jira_projects(jira_projects_view: JiraProjects = Depends()):
    return jira_projects_view.list_jira_projects()


@router.get(
    "/jira-projects/{jira_project_id}",
    response_model=JiraProject,
    **_kwargs_jira_projects,
)
def get_jira_project(
    jira_project_id: str, jira_projects_view: JiraProjects = Depends()
):
    return jira_projects_view.get_jira_project(jira_project_id)


@router.get(
    "/jira-projects/{jira_project_id}/jira-issuetypes",
    response_model=list[JiraIssueType],
    tags=["jira-issue-type"],
)
def get_jira_issue_types(
    jira_project_id: str, jira_issue_types_view: JiraIssueTypes = Depends()
):
    return jira_issue_types_view.list_jira_issue_types(jira_project_id)


_kwargs_jira_issues = dict(tags=["jira-issue"])


@router.get(
    "/jira-projects/{jira_project_id}/jira-issues",
    response_model=list[JiraIssue],
    **_kwargs_jira_issues,
)
def get_jira_issues(
    jira_project_id: str,
    offset: conint(ge=0) = 0,
    limit: conint(ge=0) | None = None,
    jira_issues_view: JiraIssues = Depends(),
) -> Iterator[JiraIssue]:
    return jira_issues_view.list_jira_issues(jira_project_id, offset, limit)


@router.post(
    "/jira-projects/{jira_project_id}/jira-issues",
    status_code=201,
    response_model=JiraIssue,
    **_kwargs_jira_issues,
)
def create_jira_issue(
    jira_project_id: str,
    jira_issue_input: JiraIssueInput,
    jira_issues_view: JiraIssues = Depends(),
) -> JiraIssue:
    return jira_issues_view.create_jira_issue(jira_project_id, jira_issue_input)


@router.get(
    "/jira-issues/{jira_issue_id}", response_model=JiraIssue, **_kwargs_jira_issues
)
def get_jira_issue(
    jira_issue_id: str, jira_issues_view: JiraIssues = Depends()
) -> JiraIssue:
    return jira_issues_view.get_jira_issue(jira_issue_id)


@router.put(
    "/jira-issues/{jira_issue_id}", response_model=JiraIssue, **_kwargs_jira_issues
)
def update_jira_issue(
    jira_issue_id: str,
    jira_issue_input: JiraIssueInput,
    jira_issues_view: JiraIssues = Depends(),
) -> JiraIssue:
    return jira_issues_view.update_jira_issue(jira_issue_id, jira_issue_input)


@router.delete(
    "/jira-issues/{jira_issue_id}",
    status_code=204,
    response_class=Response,
    **_kwargs_jira_issues,
)
def delete_jira_issue(jira_issue_id: str, jira_issues_view: JiraIssues = Depends()):
    jira_issues_view.delete_jira_issue(jira_issue_id)