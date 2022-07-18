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

import pytest
from jira import JIRAError
from mvtool.models import JiraIssue, JiraIssueInput
from mvtool.views.jira_ import JiraBaseView, JiraIssueTypesView, JiraIssuesView, JiraProjectsView, JiraUserView

def test_get_jira_item_url(jira_mock):
    item_key = 'key'
    item_url = JiraBaseView(jira_mock)._get_jira_item_url(item_key)
    assert item_url == f'{jira_mock.server_url}/browse/{item_key}'

@pytest.fixture
def jira_user_mock():
    return dict(displayName='name', emailAddress='email')

def test_get_jira_user(jira_mock, jira_user_mock):
    jira_mock.myself.return_value = jira_user_mock
    jira_user = JiraUserView(jira_mock).get_jira_user()
    assert jira_user.display_name == jira_user_mock['displayName']
    assert jira_user.email_address == jira_user_mock['emailAddress']

@pytest.fixture
def jira_issue_type_mock():
    class JiraIssueTypeMock:
        def __init__(self):
            self.id = '1'
            self.name = 'name'
    return JiraIssueTypeMock()

@pytest.fixture
def jira_project_mock(jira_issue_type_mock):
    class JiraProjectMock:
        def __init__(self):
            self.id = '1'
            self.name = 'name'
            self.key = 'key'
            self.issueTypes = [jira_issue_type_mock]
    return JiraProjectMock()

def test_list_jira_projects(jira_mock, jira_project_mock):
    jira_mock.projects.return_value = [jira_project_mock]
    jira_projects = list(JiraProjectsView(jira_mock).list_jira_projects())
    assert jira_projects[0].id == jira_project_mock.id
    assert jira_projects[0].name == jira_project_mock.name
    assert jira_projects[0].key == jira_project_mock.key

def test_get_jira_project(jira_mock, jira_project_mock):
    jira_mock.project.return_value = jira_project_mock
    jira_project = JiraProjectsView(jira_mock).get_jira_project(jira_project_mock.id)
    assert jira_project.id == jira_project_mock.id
    assert jira_project.name == jira_project_mock.name
    assert jira_project.key == jira_project_mock.key

def test_check_jira_project_id_fails(jira_mock):
    jira_mock.project.side_effect = JIRAError('error')
    with pytest.raises(JIRAError):
        JiraProjectsView(jira_mock).check_jira_project_id('1')

def test_check_jira_project_id_succeeds(jira_mock, jira_project_mock):
    jira_mock.project.return_value = jira_project_mock
    JiraProjectsView(jira_mock).check_jira_project_id(jira_project_mock)
    jira_mock.project.assert_called_once_with(jira_project_mock)

def test_check_jira_project_id_gets_none(jira_mock):
    JiraProjectsView(jira_mock).check_jira_project_id(None)
    jira_mock.project.assert_not_called()

def test_try_to_get_jira_project_fails_not_found(jira_mock):
    jira_mock.project.side_effect = JIRAError('error', status_code=404)
    result = JiraProjectsView(jira_mock).try_to_get_jira_project('1')
    assert result is None

def test_try_to_get_jira_project_fails_other_reason(jira_mock):
    jira_mock.project.side_effect = JIRAError('error', status_code=500)
    with pytest.raises(JIRAError):
        JiraProjectsView(jira_mock).try_to_get_jira_project('1')

def test_try_to_get_jira_project_succeeds(jira_mock, jira_project_mock):
    jira_mock.project.return_value = jira_project_mock
    result = JiraProjectsView(
        jira_mock).try_to_get_jira_project(jira_project_mock.id)
    assert result.id == jira_project_mock.id
    assert result.name == jira_project_mock.name
    assert result.key == jira_project_mock.key

def test_list_jira_issue_types(
        jira_mock, jira_project_mock, jira_issue_type_mock):
    jira_mock.project.return_value = jira_project_mock
    jira_issue_types = list(JiraIssueTypesView(jira_mock).list_jira_issue_types(
        jira_project_mock.id))
    assert jira_issue_types[0].name == jira_issue_type_mock.name
    assert jira_issue_types[0].id == jira_issue_type_mock.id
    jira_mock.project.assert_called_once_with(jira_project_mock.id)

@pytest.fixture
def jira_issue_mock(jira_project_mock, jira_issue_type_mock):
    class JiraIssueStatusCategoryMock:
        colorName = 'color'
    
    class JiraIssueStatusMock:
        name = 'name'
        statusCategory = JiraIssueStatusCategoryMock
    
    class JiraIssueFieldsMock:
        summary = 'summary'
        description = 'description'
        project = jira_project_mock
        issuetype = jira_issue_type_mock
        status = JiraIssueStatusMock

    class JiraIssueMock:
        id = '1'
        key = 'key'
        fields = JiraIssueFieldsMock()
    return JiraIssueMock

def test_convert_to_jira_issue(jira_mock, jira_issue_mock):
    jira_issue = JiraIssuesView(jira_mock)._convert_to_jira_issue(jira_issue_mock)
    assert jira_issue.id == jira_issue_mock.id
    assert jira_issue.key == jira_issue_mock.key
    assert jira_issue.summary == jira_issue_mock.fields.summary
    assert jira_issue.description == jira_issue_mock.fields.description
    assert jira_issue.project_id == jira_issue_mock.fields.project.id
    assert jira_issue.issuetype_id == jira_issue_mock.fields.issuetype.id
    assert jira_issue.status.name == jira_issue_mock.fields.status.name
    assert jira_issue.status.color_name == jira_issue_mock.fields.status.statusCategory.colorName


def test_list_jira_issues(jira_mock, jira_project_mock, jira_issue_mock):
    jira_mock.search_issues.return_value = [jira_issue_mock]
    jira_issues = list(JiraIssuesView(jira_mock).list_jira_issues(jira_project_mock.id))
    assert jira_issues[0].id == jira_issue_mock.id
    assert isinstance(jira_issues[0], JiraIssue)

@pytest.fixture
def jira_issue_input(jira_issue_mock):
    return JiraIssueInput(
        summary=jira_issue_mock.fields.summary,
        description=jira_issue_mock.fields.description,
        issuetype_id=jira_issue_mock.fields.issuetype.id)

def test_create_jira_issue(jira_mock, jira_project_mock, jira_issue_mock, jira_issue_input):
    jira_mock.create_issue.return_value = jira_issue_mock
    jira_issue = JiraIssuesView(jira_mock).create_jira_issue(
        jira_project_mock.id, jira_issue_input)
    assert jira_issue.id == jira_issue_mock.id
    assert isinstance(jira_issue, JiraIssue)

def test_get_jira_issue(jira_mock, jira_issue_mock):
    jira_mock.issue.return_value = jira_issue_mock
    jira_issue = JiraIssuesView(jira_mock).get_jira_issue(jira_issue_mock.id)
    assert jira_issue.id == jira_issue_mock.id
    assert isinstance(jira_issue, JiraIssue)

def test_get_jira_issues_single_issue(jira_mock, jira_issue_mock):
    jira_mock.search_issues.return_value = [jira_issue_mock]
    jira_issues = JiraIssuesView(
        jira_mock).get_jira_issues((jira_issue_mock.id,))
    assert jira_issues[0].id == jira_issue_mock.id
    assert isinstance(jira_issues[0], JiraIssue)
    jira_mock.search_issues.assert_called_once_with(
        'id = 1', validate_query=False, startAt=0, maxResults=None)

def test_get_jira_issues_multiple_issues(jira_mock):
    jira_mock.search_issues.return_value = []
    jira_issues = JiraIssuesView(
        jira_mock).get_jira_issues(('1', '2'))
    assert jira_issues == []
    jira_mock.search_issues.assert_called_once_with(
        'id = 1 OR id = 2', validate_query=False, startAt=0, maxResults=None)

def test_check_jira_issue_id_fails(jira_mock):
    jira_mock.issue.side_effect = JIRAError('error')
    with pytest.raises(JIRAError):
        JiraIssuesView(jira_mock).check_jira_issue_id('1')

def test_check_jira_issue_id_success(jira_mock, jira_issue_mock):
    jira_mock.issue.return_value = jira_issue_mock
    JiraIssuesView(jira_mock).check_jira_issue_id('1')
    jira_mock.issue.assert_called_once_with(id='1')

def test_check_jira_issue_id_gets_none(jira_mock):
    JiraIssuesView(jira_mock).check_jira_issue_id(None)
    jira_mock.issue.assert_not_called()

def test_try_to_get_jira_issue_fails_not_found(jira_mock):
    jira_mock.issue.side_effect = JIRAError('error', status_code=404)
    result = JiraIssuesView(jira_mock).try_to_get_jira_issue('1')
    assert result is None

def test_try_to_get_jira_issue_fails_other_reason(jira_mock):
    jira_mock.issue.side_effect = JIRAError('error', status_code=500)
    with pytest.raises(JIRAError):
        JiraIssuesView(jira_mock).try_to_get_jira_issue('1')

def test_try_to_get_jira_issue_succeeds(jira_mock, jira_issue_mock):
    jira_mock.issue.return_value = jira_issue_mock
    result = JiraIssuesView(jira_mock).try_to_get_jira_issue(jira_issue_mock.id)
    assert result.id == jira_issue_mock.id
    assert isinstance(result, JiraIssue)
    jira_mock.issue.assert_called_once_with(id=jira_issue_mock.id)