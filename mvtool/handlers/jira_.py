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


from fastapi import APIRouter, Depends, Query, Response

from ..data.jira_ import JiraIssues, JiraIssueTypes, JiraProjects, JiraUsers
from ..models import JiraIssue, JiraIssueInput, JiraIssueType, JiraProject, JiraUser
from ..utils.pagination import Page, page_params

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


def get_jira_issue_filters(
    # Filter by values
    ids: list[str] | None = Query(None),
    keys: list[str] | None = Query(None),
    jira_project_ids: list[str] | None = None,
    #
    # Filter by search string
    search: str | None = None,
):
    clauses = []

    # Filter by values
    for name, values in (
        ("id", ids),
        ("key", keys),
        ("project", jira_project_ids),
    ):
        if not values:
            continue
        elif len(values) == 1:
            clauses.append(f"{name} = {values[0]}")
        else:
            clauses.append(f"{name} IN ({', '.join(values)})")

    # Filter by search string
    if search:
        clauses.append(f'text ~ "{search}"')

    return " AND ".join(clauses)


@router.get(
    "/jira-projects/{jira_project_id}/jira-issues",
    response_model=Page[JiraIssue] | list[JiraIssue],
    **_kwargs_jira_issues,
)
def get_jira_issues(
    jira_project_id: str,
    page_params=Depends(page_params),
    jira_issues_view: JiraIssues = Depends(),
):
    jql_str = get_jira_issue_filters(
        ids=None, keys=None, jira_project_ids=[jira_project_id]
    )

    # Convert iterator to a list to force running the JIRA query in list_jira_issues()
    jira_issues = list(jira_issues_view.list_jira_issues(jql_str, **page_params))

    if page_params:
        return Page[JiraIssue](
            items=jira_issues,
            total_count=jira_issues_view.count_jira_issues(jql_str),
        )
    else:
        return jira_issues


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
