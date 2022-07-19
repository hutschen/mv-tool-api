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
from mvtool.models import Project, ProjectInput, ProjectOutput

from mvtool.views.projects import ProjectsView


@pytest.fixture
def jira_projects_view_mock():
    return Mock()

@pytest.fixture
def crud_mock():
    return Mock()

@pytest.fixture
def project_input(jira_project_mock):
    return ProjectInput(
        name='name', description='description', jira_project_id=jira_project_mock.id)

@pytest.fixture
def project(project_input):
    return Project.from_orm(project_input, update=dict(id=1))

@pytest.fixture
def project_output(project):
    return ProjectOutput.from_orm(project)

def test_list_projects(jira_projects_view_mock, crud_mock, project):
    crud_mock.list_from_db.return_value = [project]
    result = ProjectsView(jira_projects_view_mock, crud_mock).list_projects()
    assert result == [project]
    crud_mock.read_all_from_db.assert_called_once_with(Project)

def test_create_project(
        jira_projects_view_mock, crud_mock, project_input, project):
    crud_mock.create_in_db.return_value = project
    result = ProjectsView(
        jira_projects_view_mock, crud_mock).create_project(project_input)
    assert result.id == project.id
    assert isinstance(result, Project)
    jira_projects_view_mock.check_jira_project_id.assert_called_once_with(project_input.jira_project_id)
    crud_mock.create_in_db.assert_called_once()

def test_project(project, project_output):
    assert project.id == project_output.id

@pytest.mark.skip
def test_create_project_webapi_handler():
    pass