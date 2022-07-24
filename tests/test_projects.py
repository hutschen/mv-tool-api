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
from fastapi import HTTPException
import pytest
from mvtool.database import CRUDOperations
from mvtool.models import Project, ProjectInput, ProjectOutput
from mvtool.views.jira_ import JiraProjectsView
from mvtool.views.projects import ProjectsView

@pytest.fixture
def create_project(projects_view: ProjectsView, project_input: ProjectInput):
    return projects_view.create_project(project_input)

def test_list_project_outputs(crud: CRUDOperations, create_project: Project):
    jira_projects: JiraProjectsView = Mock()
    jira_projects.list_jira_projects.return_value = []

    sut = ProjectsView(jira_projects, crud)
    results = list(sut._list_projects())

    assert len(results) == 1
    assert isinstance(results[0], ProjectOutput)
    assert results[0].id == create_project.id
    jira_projects.list_jira_projects.assert_called_once()

def test_create_project_output(crud: CRUDOperations, project_input: ProjectInput):
    jira_projects: JiraProjectsView = Mock()
    jira_projects.check_jira_project_id.return_value = None
    jira_projects.try_to_get_jira_project.return_value = None
    project_input.jira_project_id = '1000'

    sut = ProjectsView(jira_projects, crud)
    result = sut._create_project(project_input)

    assert isinstance(result, ProjectOutput)
    jira_projects.check_jira_project_id.assert_called_with(
        project_input.jira_project_id)

def test_get_project_output(crud: CRUDOperations, create_project: Project):
    jira_projects = Mock()
    jira_projects.try_to_get_jira_project.return_value = None

    sut = ProjectsView(jira_projects, crud)
    result = sut._get_project(create_project.id)

    assert isinstance(result, ProjectOutput)

def test_update_project_output(
        crud: CRUDOperations, project_input: ProjectInput, 
        create_project: Project):
    jira_projects = Mock()
    jira_projects.check_jira_project_id.return_value = None
    jira_projects.try_to_get_jira_project.return_value = None

    orig_project_name = project_input.name
    project_input.name += ' (updated)'
    assert project_input.name != orig_project_name

    sut = ProjectsView(jira_projects, crud)
    result = sut._update_project(create_project.id, project_input)

    assert isinstance(result, ProjectOutput)
    assert result.name == project_input.name

def test_delete_project(crud: CRUDOperations, create_project: Project):
    sut = ProjectsView(None, crud)
    result = sut.delete_project(create_project.id)
    assert result is None

    with pytest.raises(HTTPException) as exception_info:
        sut.delete_project(create_project.id)
        assert exception_info.value.status_code == 404