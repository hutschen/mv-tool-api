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

import pytest
from jira import JIRAError
from mvtool.models import (
    JiraIssue,
    JiraIssueType,
    JiraProject,
    JiraUser,
)
from mvtool.data.jira_ import (
    JiraBase,
    JiraIssueTypes,
    JiraIssues,
    JiraProjects,
    JiraUsers,
)


def test_get_jira_item_url(jira):
    item_key = "key"
    item_url = JiraBase(jira)._get_jira_item_url(item_key)
    assert item_url == f"{jira.server_url}/browse/{item_key}"


def test_get_jira_user(jira, jira_user_data):
    jira.myself.return_value = jira_user_data
    result = JiraUsers(jira).get_jira_user()
    assert isinstance(result, JiraUser)
    assert result.display_name == jira_user_data["displayName"]
    assert result.email_address == jira_user_data["emailAddress"]


def test_lookup_or_try_to_get_jira_project(jira, jira_project_data):
    jira.project.return_value = jira_project_data
    jira_projects_view = JiraProjects(jira)

    result = jira_projects_view.lookup_jira_project(
        jira_project_data.id, try_to_get=True
    )

    assert isinstance(result, JiraProject)
    assert result.id == jira_project_data.id
    assert jira_projects_view._jira_projects_cache == {jira_project_data.id: result}


def test_lookup_jira_project(jira, jira_project_data):
    jira.project.return_value = jira_project_data
    jira_projects_view = JiraProjects(jira)

    result = jira_projects_view.lookup_jira_project(
        jira_project_data.id, try_to_get=False
    )

    assert result is None
    assert jira_projects_view._jira_projects_cache == {}


def test_list_jira_projects(jira, jira_project_data):
    jira.projects.return_value = [jira_project_data]
    results = list(JiraProjects(jira).list_jira_projects())
    assert isinstance(results[0], JiraProject)
    assert results[0].id == jira_project_data.id


def test_get_jira_project(jira, jira_project_data):
    jira.project.return_value = jira_project_data
    result = JiraProjects(jira).get_jira_project(jira_project_data.id)
    assert isinstance(result, JiraProject)
    assert result.id == jira_project_data.id


def test_check_jira_project_id_fails(jira):
    jira.project.side_effect = JIRAError("error")
    with pytest.raises(JIRAError):
        JiraProjects(jira).check_jira_project_id("1")


def test_check_jira_project_id_succeeds(jira, jira_project_data):
    jira.project.return_value = jira_project_data
    JiraProjects(jira).check_jira_project_id(jira_project_data.id)
    jira.project.assert_called_once_with(jira_project_data.id)


def test_check_jira_project_id_gets_none(jira):
    JiraProjects(jira).check_jira_project_id(None)
    jira.project.assert_not_called()


def test_try_to_get_jira_project_fails_not_found(jira):
    jira.project.side_effect = JIRAError("error", status_code=404)
    result = JiraProjects(jira).try_to_get_jira_project("1")
    assert result is None


def test_try_to_get_jira_project_fails_other_reason(jira):
    jira.project.side_effect = JIRAError("error", status_code=500)
    with pytest.raises(JIRAError):
        JiraProjects(jira).try_to_get_jira_project("1")


def test_try_to_get_jira_project_succeeds(jira, jira_project_data):
    jira.project.return_value = jira_project_data
    result = JiraProjects(jira).try_to_get_jira_project(jira_project_data.id)
    assert isinstance(result, JiraProject)
    assert result.id == jira_project_data.id


def test_try_to_get_jira_project_gets_none(jira):
    result = JiraProjects(jira).try_to_get_jira_project(None)
    assert result is None


def test_list_jira_issue_types(jira, jira_project_data, jira_issue_type_data):
    jira.project.return_value = jira_project_data
    results = list(JiraIssueTypes(jira).list_jira_issue_types(jira_project_data.id))
    assert isinstance(results[0], JiraIssueType)
    assert results[0].id == jira_issue_type_data.id
    jira.project.assert_called_once_with(jira_project_data.id)


def test_convert_to_jira_issue(jira, jira_issue_data):
    result = JiraIssues(jira)._convert_to_jira_issue(jira_issue_data)
    assert isinstance(result, JiraIssue)
    assert result.id == jira_issue_data.id
    assert result.key == jira_issue_data.key
    assert result.summary == jira_issue_data.fields.summary
    assert result.description == jira_issue_data.fields.description
    assert result.project_id == jira_issue_data.fields.project.id
    assert result.issuetype_id == jira_issue_data.fields.issuetype.id
    assert result.status.name == jira_issue_data.fields.status.name
    assert (
        result.status.color_name
        == jira_issue_data.fields.status.statusCategory.colorName
    )


def test_lookup_or_try_to_get_jira_issue(jira, jira_issue_data):
    jira.issue.return_value = jira_issue_data
    jira_issues_view = JiraIssues(jira)

    result = jira_issues_view.lookup_jira_issue(jira_issue_data.id, try_to_get=True)

    assert isinstance(result, JiraIssue)
    assert result.id == jira_issue_data.id
    assert jira_issues_view._jira_issues_cache == {jira_issue_data.id: result}


def test_lookup_jira_issue(jira, jira_issue_data):
    jira.issue.return_value = jira_issue_data
    jira_issues_view = JiraIssues(jira)

    result = jira_issues_view.lookup_jira_issue(jira_issue_data.id, try_to_get=False)

    assert result is None
    assert jira_issues_view._jira_issues_cache == {}


def test_list_jira_issues(jira, jira_project_data, jira_issue_data):
    jira.search_issues.return_value = [jira_issue_data]
    jira_issues = list(JiraIssues(jira).list_jira_issues(jira_project_data.id))
    assert isinstance(jira_issues[0], JiraIssue)
    assert jira_issues[0].id == jira_issue_data.id


def test_create_jira_issue(jira, jira_project_data, jira_issue_data, jira_issue_input):
    jira.create_issue.return_value = jira_issue_data
    result = JiraIssues(jira).create_jira_issue(jira_project_data.id, jira_issue_input)
    assert isinstance(result, JiraIssue)
    assert result.id == jira_issue_data.id


def test_get_jira_issue(jira, jira_issue_data):
    jira.issue.return_value = jira_issue_data
    result = JiraIssues(jira).get_jira_issue(jira_issue_data.id)
    assert isinstance(result, JiraIssue)
    assert result.id == jira_issue_data.id


def test_get_jira_issues_single_issue(jira, jira_issue_data):
    jira.search_issues.return_value = [jira_issue_data]
    results = list(JiraIssues(jira).get_jira_issues((jira_issue_data.id,)))
    assert isinstance(results[0], JiraIssue)
    assert results[0].id == jira_issue_data.id
    jira.search_issues.assert_called_once_with(
        "id = 1", validate_query=False, startAt=0, maxResults=None
    )


def test_get_jira_issues_multiple_issues(jira):
    jira.search_issues.return_value = []
    result = list(JiraIssues(jira).get_jira_issues(("1", "2")))
    assert result == []
    jira.search_issues.assert_called_once_with(
        "id = 1 OR id = 2", validate_query=False, startAt=0, maxResults=None
    )


def test_get_jira_issues_no_issues(jira):
    jira.search_issues.return_value = []
    result = list(JiraIssues(jira).get_jira_issues([]))
    assert result == []
    jira.search_issues.assert_not_called()


def test_check_jira_issue_id_fails(jira):
    jira.issue.side_effect = JIRAError("error")
    with pytest.raises(JIRAError):
        JiraIssues(jira).check_jira_issue_id("1")


def test_check_jira_issue_id_success(jira, jira_issue_data):
    jira.issue.return_value = jira_issue_data
    JiraIssues(jira).check_jira_issue_id(jira_issue_data.id)
    jira.issue.assert_called_once_with(jira_issue_data.id)


def test_check_jira_issue_id_gets_none(jira):
    JiraIssues(jira).check_jira_issue_id(None)
    jira.issue.assert_not_called()


def test_try_to_get_jira_issue_fails_not_found(jira):
    jira.issue.side_effect = JIRAError("error", status_code=404)
    result = JiraIssues(jira).try_to_get_jira_issue("1")
    assert result is None


def test_try_to_get_jira_issue_fails_other_reason(jira):
    jira.issue.side_effect = JIRAError("error", status_code=500)
    with pytest.raises(JIRAError):
        JiraIssues(jira).try_to_get_jira_issue("1")


def test_try_to_get_jira_issue_succeeds(jira, jira_issue_data):
    jira.issue.return_value = jira_issue_data
    result = JiraIssues(jira).try_to_get_jira_issue(jira_issue_data.id)
    assert result.id == jira_issue_data.id
    assert isinstance(result, JiraIssue)
    jira.issue.assert_called_once_with(jira_issue_data.id)


def test_try_to_get_jira_issue_gets_none(jira):
    result = JiraIssues(jira).try_to_get_jira_issue(None)
    assert result is None


def test_update_jira_issue(jira, jira_issue_data, jira_issue_input):
    result = JiraIssues(jira).update_jira_issue(jira_issue_data.id, jira_issue_input)
    assert isinstance(result, JiraIssue)
    assert result.id == jira_issue_data.id
    jira.issue.assert_called_once_with(jira_issue_data.id)
    jira_issue_data.update.assert_called_once_with(
        summary=jira_issue_input.summary,
        description=jira_issue_input.description,
        issuetype={"id": jira_issue_input.issuetype_id},
    )


def test_delete_jira_issue(jira, jira_issue_data):
    JiraIssues(jira).delete_jira_issue(jira_issue_data.id)
    jira.issue.assert_called_once_with(jira_issue_data.id)
    jira_issue_data.delete.assert_called_once_with()
