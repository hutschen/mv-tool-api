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
from mvtool.config import Config
from mvtool.models import JiraIssueInput

@pytest.fixture
def config():
    return Config(
        sqlite_url='sqlite://',
        sqlite_echo=False,
        jira_server_url='http://jira-server-url',)

@pytest.fixture
def jira(config):
    jira = Mock()
    jira.server_url = config.jira_server_url
    return jira

@pytest.fixture
def jira_user():
    return dict(displayName='name', emailAddress='email')

@pytest.fixture
def jira_issue_type():
    class JiraIssueTypeMock:
        def __init__(self):
            self.id = '1'
            self.name = 'name'
    return JiraIssueTypeMock()

@pytest.fixture
def jira_project(jira_issue_type):
    class JiraProjectMock:
        def __init__(self):
            self.id = '1'
            self.name = 'name'
            self.key = 'key'
            self.issueTypes = [jira_issue_type]
    return JiraProjectMock()

@pytest.fixture
def jira_issue(jira_project, jira_issue_type):
    class JiraIssueStatusCategoryMock:
        colorName = 'color'
    
    class JiraIssueStatusMock:
        name = 'name'
        statusCategory = JiraIssueStatusCategoryMock
    
    class JiraIssueFieldsMock:
        summary = 'summary'
        description = 'description'
        project = jira_project
        issuetype = jira_issue_type
        status = JiraIssueStatusMock

    class JiraIssueMock:
        id = '1'
        key = 'key'
        fields = JiraIssueFieldsMock()
    return JiraIssueMock

@pytest.fixture
def jira_issue_input(jira_issue):
    return JiraIssueInput(
        summary=jira_issue.fields.summary,
        description=jira_issue.fields.description,
        issuetype_id=jira_issue.fields.issuetype.id)