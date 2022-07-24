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
from mvtool.models import DocumentInput, JiraIssueInput, MeasureInput, ProjectInput, Project, ProjectOutput, Requirement, RequirementInput, RequirementOutput

@pytest.fixture
def config():
    return Config(
        sqlite_url='sqlite://',
        sqlite_echo=False,
        jira_server_url='http://jira-server-url',)

@pytest.fixture
def jira(config):
    ''' Mocks JIRA API object. '''
    jira = Mock()
    jira.server_url = config.jira_server_url
    return jira

@pytest.fixture
def jira_user_data():
    ''' Mocks response from JIRA API for user data. '''
    return dict(displayName='name', emailAddress='email')

@pytest.fixture
def jira_issue_type_data():
    ''' Mocks response data from JIRA API for issue type. '''
    class JiraIssueTypeMock:
        def __init__(self):
            self.id = '1'
            self.name = 'name'
    return JiraIssueTypeMock()

@pytest.fixture
def jira_project_data(jira_issue_type_data):
    ''' Mocks response data from JIRA API for project. '''
    class JiraProjectMock:
        def __init__(self):
            self.id = '1'
            self.name = 'name'
            self.key = 'key'
            self.issueTypes = [jira_issue_type_data]
    return JiraProjectMock()

@pytest.fixture
def jira_issue_data(jira_project_data, jira_issue_type_data):
    ''' Mocks response data from JIRA API for issue. '''
    class JiraIssueStatusCategoryMock:
        colorName = 'color'
    
    class JiraIssueStatusMock:
        name = 'name'
        statusCategory = JiraIssueStatusCategoryMock
    
    class JiraIssueFieldsMock:
        summary = 'summary'
        description = 'description'
        project = jira_project_data
        issuetype = jira_issue_type_data
        status = JiraIssueStatusMock

    class JiraIssueMock:
        id = '1'
        key = 'key'
        fields = JiraIssueFieldsMock()
    return JiraIssueMock

@pytest.fixture
def jira_issue_input(jira_issue_data):
    ''' Mocks input for creating or updating an JIRA issue. '''
    return JiraIssueInput(
        summary=jira_issue_data.fields.summary,
        description=jira_issue_data.fields.description,
        issuetype_id=jira_issue_data.fields.issuetype.id)

@pytest.fixture
def jira_projects_view():
    return Mock()

@pytest.fixture
def crud():
    return Mock()

@pytest.fixture
def project_input():
    return ProjectInput(name='name')

@pytest.fixture
def project(project_input):
    return Project.from_orm(project_input, update=dict(id=1))

@pytest.fixture
def project_output(project):
    return ProjectOutput.from_orm(project)

@pytest.fixture()
def document_input():
    return DocumentInput(title='title')

@pytest.fixture
def requirement_input():
    return RequirementInput(summary='summary')

@pytest.fixture
def requirement(requirement_input):
    return Requirement.from_orm(requirement_input, update=dict(id=1))

@pytest.fixture
def requirement_output(requirement, project):
    requirement.project_id = project.id
    requirement.project = project
    return RequirementOutput.from_orm(requirement)

@pytest.fixture()
def measure_input():
    return MeasureInput(summary='summary')

@pytest.fixture
def projects_view():
    return Mock()