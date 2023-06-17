# coding: utf-8
#
# Copyright (C) 2023 Helmar Hutschenreuter
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

import jira
import pytest
from fastapi import HTTPException

from mvtool.data.projects import Projects
from mvtool.db.schema import Project
from mvtool.handlers.projects import (
    create_project,
    delete_project,
    get_project,
    get_project_field_names,
    get_project_representations,
    get_projects,
    update_project,
)
from mvtool.models.projects import (
    ProjectInput,
    ProjectOutput,
    ProjectRepresentation,
)
from mvtool.utils.pagination import Page


def test_get_projects_list(projects: Projects, project: Project):
    projects_list = get_projects([], [], {}, projects)

    assert isinstance(projects_list, list)
    for project_ in projects_list:
        assert isinstance(project_, Project)


def test_get_projects_with_pagination(projects: Projects, project: Project):
    page_params = dict(offset=0, limit=1)
    projects_page = get_projects([], [], page_params, projects)

    assert isinstance(projects_page, Page)
    assert projects_page.total_count == 1
    for project_ in projects_page.items:
        assert isinstance(project_, ProjectOutput)


def test_create_project(projects: Projects):
    project_input = ProjectInput(name="New Project")
    created_project = create_project(project_input, projects)

    assert isinstance(created_project, Project)
    assert created_project.name == project_input.name


def test_get_project(projects: Projects, project: Project):
    project_id = project.id
    retrieved_project = get_project(project_id, projects)

    assert isinstance(retrieved_project, Project)
    assert retrieved_project.id == project_id


def test_update_project(projects: Projects, project: Project):
    project_id = project.id
    project_input = ProjectInput(name="Updated Project")
    updated_project = update_project(project_id, project_input, projects)

    assert isinstance(updated_project, Project)
    assert updated_project.id == project_id
    assert updated_project.name == project_input.name


def test_delete_project(projects: Projects, project: Project):
    project_id = project.id
    delete_project(project_id, projects)

    with pytest.raises(HTTPException) as excinfo:
        get_project(project_id, projects)
    assert excinfo.value.status_code == 404
    assert "No Project with id" in excinfo.value.detail


def test_get_project_representations_list(projects: Projects, project: Project):
    results = get_project_representations([], None, [], {}, projects)

    assert isinstance(results, list)
    for item in results:
        assert isinstance(item, Project)


def test_get_project_representations_with_pagination(
    projects: Projects, project: Project
):
    page_params = dict(offset=0, limit=1)
    resulting_page = get_project_representations([], None, [], page_params, projects)

    assert isinstance(resulting_page, Page)
    assert resulting_page.total_count == 1
    for item in resulting_page.items:
        assert isinstance(item, ProjectRepresentation)


def test_get_project_representations_local_search(projects: Projects):
    # Create two projects with different names
    project_inputs = [
        ProjectInput(name="Apple Project"),
        ProjectInput(name="Banana Project"),
    ]
    for project_input in project_inputs:
        projects.create_project(project_input)

    # Get representations using local_search to filter the projects
    local_search = "Banana"
    project_representations_list = get_project_representations(
        [], local_search, [], {}, projects
    )

    # Check if the correct project is returned after filtering
    assert isinstance(project_representations_list, list)
    assert len(project_representations_list) == 1
    project = project_representations_list[0]
    assert isinstance(project, Project)
    assert project.name == "Banana Project"


def test_get_project_field_names_default_list(projects: Projects):
    field_names = get_project_field_names([], projects)

    assert isinstance(field_names, set)
    assert field_names == {"id", "name"}


def test_get_project_field_names_full_list(
    projects: Projects, jira_project_data: jira.Project
):
    # Create a project to get all fields
    project_input = ProjectInput(
        name="Example Project",
        description="Example description",
        jira_project_id=jira_project_data.id,
    )
    projects.create_project(project_input)

    field_names = get_project_field_names([], projects)

    # Check if all field names are returned
    assert isinstance(field_names, set)
    assert field_names == {"id", "name", "description", "jira_project"}
