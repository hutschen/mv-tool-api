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
from unittest.mock import Mock
from jira import JIRAError
from mvtool.views.jira_ import JiraBaseView, JiraProjectsView, JiraUserView

@pytest.fixture
def jira_mock():
    jira = Mock()
    jira.server_url = 'https://...'
    return jira

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
def jira_project_mock():
    class JiraProjectMock:
        def __init__(self):
            self.id = '1'
            self.name = 'name'
            self.key = 'key'
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
