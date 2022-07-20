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

from unittest.mock import Mock
import pytest
from mvtool.database import CRUDOperations
from mvtool.models import ProjectInput, Project, ProjectOutput
from mvtool.views.jira_ import JiraProjectsView

from mvtool.views.projects import ProjectsView

@pytest.fixture
def jira_projects_view():
    return Mock()

@pytest.fixture
def crud():
    return Mock()

@pytest.fixture
def project_input():
    return ProjectInput(
        name='name', description='description', jira_project_id=None)

@pytest.fixture
def project(project_input):
    return Project.from_orm(project_input, update=dict(id=1))

@pytest.fixture
def project_output(project):
    return ProjectOutput.from_orm(project)

def test_list_projects(jira_projects_view: JiraProjectsView, crud: CRUDOperations, project):
    crud.read_all_from_db.return_value = [project]
    jira_projects_view.list_jira_projects.return_value = []

    sut = ProjectsView(jira_projects_view, crud)
    results = list(sut._list_projects())

    assert isinstance(results[0], ProjectOutput)
    assert results[0].id == project.id
    crud.read_all_from_db.assert_called_once()
    jira_projects_view.list_jira_projects.assert_called_once()

def test_create_project(jira_projects_view: JiraProjectsView, crud: CRUDOperations, project_input, project):
    crud.create_in_db.return_value = project
    jira_projects_view.check_jira_project_id.return_value = None

    sut = ProjectsView(jira_projects_view, crud)
    result = sut._create_project(project_input)

    assert isinstance(result, ProjectOutput)
    assert result.id == project.id
    crud.create_in_db.assert_called_once()
    jira_projects_view.check_jira_project_id.assert_called_once()

def test_get_project(jira_projects_view: JiraProjectsView, crud: CRUDOperations, project):
    crud.read_from_db.return_value = project
    jira_projects_view.try_to_get_jira_project.return_value = None

    sut = ProjectsView(jira_projects_view, crud)
    result = sut._get_project(1)

    assert isinstance(result, ProjectOutput)
    assert result.id == project.id
    assert result.jira_project is None
    crud.read_from_db.assert_called_once()
    jira_projects_view.try_to_get_jira_project.assert_called_once()

def test_update_project(jira_projects_view: JiraProjectsView, crud: CRUDOperations, project_input, project):
    crud.update_in_db.return_value = project
    jira_projects_view.check_jira_project_id.return_value = None

    sut = ProjectsView(jira_projects_view, crud)
    result = sut._update_project(project.id, project_input)

    assert isinstance(result, ProjectOutput)
    assert result.id == project.id
    crud.update_in_db.assert_called_once()
    jira_projects_view.check_jira_project_id.assert_called_once()

def test_delete_project(jira_projects_view: JiraProjectsView, crud: CRUDOperations, project):
    crud.delete_in_db.return_value = None

    sut = ProjectsView(jira_projects_view, crud)
    result = sut.delete_project(1)

    assert result is None
    crud.delete_in_db.assert_called_once()