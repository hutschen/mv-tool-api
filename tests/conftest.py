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


from unittest.mock import Mock

import jira
import pytest
from jira import JIRAError

from mvtool.db import database
from mvtool.config import Config, DatabaseConfig, JiraConfig
from mvtool.db.schema import Catalog, CatalogModule, Project, Requirement
from mvtool.handlers.catalog_modules import CatalogModules
from mvtool.handlers.catalog_requirements import CatalogRequirements
from mvtool.handlers.catalogs import Catalogs
from mvtool.handlers.documents import Documents
from mvtool.handlers.jira_ import JiraIssues, JiraProjects
from mvtool.handlers.measures import Measures
from mvtool.handlers.projects import Projects
from mvtool.handlers.requirements import Requirements
from mvtool.models import (
    CatalogInput,
    CatalogModuleInput,
    CatalogRequirementInput,
    DocumentInput,
    JiraIssue,
    JiraIssueInput,
    JiraIssueStatus,
    MeasureInput,
    ProjectInput,
    RequirementInput,
)
from mvtool.models.jira_ import JiraProject
from mvtool.utils.temp_file import get_temp_file


@pytest.fixture
def config():
    return Config(
        database=DatabaseConfig(url="sqlite://"),
        jira=JiraConfig(url="http://jira-server-url"),
    )


@pytest.fixture
def jira_user_data():
    """Mocks response from JIRA API for user data."""
    return dict(accountId="1", displayName="name", emailAddress="email")


@pytest.fixture
def jira_issue_type_data():
    """Mocks response data from JIRA API for issue type."""

    class JiraIssueTypeMock:
        id = "1"
        name = "name"

    return JiraIssueTypeMock()


@pytest.fixture
def jira_project_data(jira_issue_type_data):
    """Mocks response data from JIRA API for project."""

    class JiraProjectMock:
        id = "1"
        name = "name"
        key = "key"
        issueTypes = [jira_issue_type_data]

    return JiraProjectMock()


@pytest.fixture
def jira_issue_data(jira_project_data, jira_issue_type_data):
    """Mocks response data from JIRA API for issue."""

    class JiraIssueStatusCategoryMock:
        colorName = "color"

    class JiraIssueStatusMock:
        name = "name"
        statusCategory = JiraIssueStatusCategoryMock

    class JiraIssueFieldsMock:
        summary = "summary"
        description = "description"
        project = jira_project_data
        issuetype = jira_issue_type_data
        status = JiraIssueStatusMock

    class JiraIssueMock:
        id = "1"
        key = "key"
        fields = JiraIssueFieldsMock()
        update = Mock()
        delete = Mock()

    return JiraIssueMock


@pytest.fixture
def jira_issue_input(jira_issue_data):
    """Mocks input for creating or updating an JIRA issue."""
    return JiraIssueInput(
        summary=jira_issue_data.fields.summary,
        description=jira_issue_data.fields.description,
        issuetype_id=jira_issue_data.fields.issuetype.id,
    )


@pytest.fixture
def jira_issue_status(jira_issue_data):
    """Mocks JIRA issue status."""
    return JiraIssueStatus(
        name=jira_issue_data.fields.status.name,
        color_name=jira_issue_data.fields.status.statusCategory.colorName,
        completed=False,
    )


@pytest.fixture
def jira_project(jira_project_data: jira.Project):
    """Mocks JIRA project."""
    return JiraProject(
        id=jira_project_data.id,
        name=jira_project_data.name,
        key=jira_project_data.key,
        url=f"http://jira-server-url/browse/{jira_project_data.key}",
    )


@pytest.fixture
def jira_issue(jira_issue_data, jira_project, jira_issue_status):
    """Mocks JIRA issue."""
    return JiraIssue(
        id=jira_issue_data.id,
        key=jira_issue_data.key,
        summary=jira_issue_data.fields.summary,
        description=jira_issue_data.fields.description,
        issuetype_id=jira_issue_data.fields.issuetype.id,
        project=jira_project,
        status=jira_issue_status,
        url=f"http://jira-server-url/browse/{jira_issue_data.key}",
    )


@pytest.fixture
def jira(config, jira_user_data, jira_project_data, jira_issue_data):
    """Mocks JIRA API object."""

    class JiraMock:
        def __init__(self):
            self.server_url = config.jira.url

        def myself(self):
            return jira_user_data

        def projects(self):
            return [jira_project_data]

        def project(self, id):
            if id == jira_project_data.id:
                return jira_project_data
            else:
                raise JIRAError("Project not found", 404)

        def search_issues(*args, **_):
            return [jira_issue_data]

        def create_issue(*args, **_):
            return jira_issue_data

        def issue(self, id):
            if id == jira_issue_data.id:
                return jira_issue_data
            else:
                raise JIRAError("Issue not found", 404)

    return Mock(wraps=JiraMock())


@pytest.fixture
def jira_projects(jira):
    return Mock(wraps=JiraProjects(jira))


@pytest.fixture
def jira_issues(jira):
    return Mock(wraps=JiraIssues(jira))


@pytest.fixture
def session(config):
    database.setup_connection(config.database)
    database.create_all()

    for session in database.get_session():
        yield session

    database.drop_all()
    database.dispose_connection()


@pytest.fixture
def catalog_input():
    return CatalogInput(title="title")


@pytest.fixture
def catalog_module_input():
    return CatalogModuleInput(title="title")


@pytest.fixture
def catalog_requirement_input():
    return CatalogRequirementInput(summary="title")


@pytest.fixture
def project_input(jira_project_data):
    return ProjectInput(name="name", jira_project_id=jira_project_data.id)


@pytest.fixture
def document_input():
    return DocumentInput(title="title")


@pytest.fixture
def requirement_input(create_catalog_requirement):
    return RequirementInput(
        summary="summary", catalog_requirement_id=create_catalog_requirement.id
    )


@pytest.fixture()
def measure_input(create_document, jira_issue_data):
    return MeasureInput(
        summary="summary",
        document_id=create_document.id,
        jira_issue_id=jira_issue_data.id,
    )


@pytest.fixture
def catalogs_view(session, jira):
    return Mock(wraps=Catalogs(session, jira))


@pytest.fixture
def create_catalog(catalogs_view: Catalogs, catalog_input: CatalogInput):
    return catalogs_view.create_catalog(catalog_input)


@pytest.fixture
def catalog_modules_view(catalogs_view, session):
    return Mock(wraps=CatalogModules(catalogs_view, session))


@pytest.fixture
def create_catalog_module(
    catalog_modules_view: CatalogModules,
    create_catalog: Catalog,
    catalog_module_input: CatalogModuleInput,
):
    return catalog_modules_view.create_catalog_module(
        create_catalog, catalog_module_input
    )


@pytest.fixture
def projects_view(jira_projects, session):
    return Mock(wraps=Projects(jira_projects, session))


@pytest.fixture
def create_project(projects_view: Projects, project_input: ProjectInput):
    return projects_view.create_project(project_input)


@pytest.fixture
def requirements_view(
    projects_view: Projects,
    catalog_requirements_view: CatalogRequirements,
    session,
):
    return Mock(wraps=Requirements(projects_view, catalog_requirements_view, session))


@pytest.fixture
def create_requirement(
    requirements_view: Requirements,
    create_project: Project,
    requirement_input: RequirementInput,
):
    return requirements_view.create_requirement(create_project, requirement_input)


@pytest.fixture
def catalog_requirements_view(catalog_modules_view: CatalogModules, session):
    return Mock(wraps=CatalogRequirements(catalog_modules_view, session))


@pytest.fixture
def create_catalog_requirement(
    catalog_requirements_view: CatalogRequirements,
    create_catalog_module: CatalogModule,
    catalog_requirement_input: CatalogRequirementInput,
):
    return catalog_requirements_view.create_catalog_requirement(
        create_catalog_module, catalog_requirement_input
    )


@pytest.fixture
def documents_view(projects_view, session):
    return Mock(wraps=Documents(projects_view, session))


@pytest.fixture
def create_document(
    documents_view: Documents,
    create_project: Project,
    document_input: DocumentInput,
):
    return documents_view.create_document(create_project, document_input)


@pytest.fixture
def measures_view(jira_issues, requirements_view, documents_view, session):
    return Mock(wraps=Measures(jira_issues, requirements_view, documents_view, session))


@pytest.fixture
def create_measure(
    measures_view: Measures,
    create_requirement: Requirement,
    measure_input: MeasureInput,
):
    return measures_view.create_measure(create_requirement, measure_input)


@pytest.fixture
def word_temp_file():
    for file in get_temp_file(".docx")():
        yield file
