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

from jira import JIRAError
import pytest
from unittest.mock import Mock
from mvtool.config import Config
from mvtool import database
from mvtool.models import Document, DocumentInput, JiraIssueInput, Measure, MeasureInput, ProjectInput, Project, ProjectOutput, Requirement, RequirementInput, RequirementOutput
from mvtool.views.documents import DocumentsView
from mvtool.views.jira_ import JiraIssuesView, JiraProjectsView
from mvtool.views.projects import ProjectsView
from mvtool.views.requirements import RequirementsView
from mvtool.views.measures import MeasuresView

@pytest.fixture
def config():
    return Config(
        sqlite_url='sqlite://',
        sqlite_echo=False,
        jira_server_url='http://jira-server-url',)

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
def jira(config, jira_user_data, jira_project_data, jira_issue_data):
    ''' Mocks JIRA API object. '''
    class JiraMock:
        def __init__(self):
            self.server_url = config.jira_server_url

        def myself(self):
            return jira_user_data

        def projects(self):
            return [jira_project_data]

        def project(self, id):
            if id == jira_project_data.id:
                return jira_project_data
            else:
                raise JIRAError('Project not found', 404)

        def search_issues(*args, **kwargs):
            return [jira_issue_data]

        def create_issue(*args, **kwargs):
            return jira_issue_data

        def issue(self, id):
            if id == jira_issue_data.id:
                return jira_issue_data
            else:
                raise JIRAError('Issue not found', 404)

    return Mock(wraps=JiraMock())

@pytest.fixture
def jira_projects_view(jira):
    return Mock(wraps=JiraProjectsView(jira))

@pytest.fixture
def jira_issues_view(jira):
    return Mock(wraps=JiraIssuesView(jira))

@pytest.fixture
def crud(config):
    database.setup_engine(config)
    database.create_all()

    for session in database.get_session():
        yield Mock(wraps=database.CRUDOperations(session))

    database.drop_all()
    database.dispose_engine()

@pytest.fixture
def project_input(jira_project_data):
    return ProjectInput(name='name', jira_project_id=jira_project_data.id)

@pytest.fixture
def document_input():
    return DocumentInput(title='title')

@pytest.fixture
def requirement_input():
    return RequirementInput(summary='summary')

@pytest.fixture()
def measure_input(create_document):
    return MeasureInput(
        summary='summary',
        document_id=create_document.id)

@pytest.fixture
def projects_view(jira_projects_view, crud):
    return Mock(wraps=ProjectsView(jira_projects_view, crud))

@pytest.fixture
def create_project(projects_view: ProjectsView, project_input: ProjectInput):
    return projects_view.create_project(project_input)

@pytest.fixture
def requirements_view(projects_view, crud):
    return Mock(wraps=RequirementsView(projects_view, crud))

@pytest.fixture
def create_requirement(
        requirements_view: RequirementsView, create_project: Project,
        requirement_input: RequirementInput):
    return requirements_view.create_requirement(
        create_project.id, requirement_input)

@pytest.fixture
def documents_view(projects_view, crud):
    return Mock(wraps=DocumentsView(projects_view, crud))

@pytest.fixture
def create_document(
        documents_view: DocumentsView, create_project: Project,
        document_input: DocumentInput):
    return documents_view.create_document(
        create_project.id, document_input)

@pytest.fixture
def measures_view(jira_issues_view, requirements_view, documents_view, crud):
    return Mock(wraps=MeasuresView(
        jira_issues_view, requirements_view, documents_view, crud))

@pytest.fixture
def create_measure(
        measures_view: MeasuresView, create_requirement: Requirement,
        measure_input: MeasureInput):
    return measures_view.create_measure(create_requirement.id, measure_input)

@pytest.fixture
def create_measure_with_jira_issue(
        measures_view: MeasuresView,  create_measure: Measure, 
        jira_issue_input: JiraIssueInput):
    measures_view.create_and_link_jira_issue(
        create_measure.id, jira_issue_input)
    return create_measure