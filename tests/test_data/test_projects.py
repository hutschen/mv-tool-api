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

from unittest.mock import Mock

import jira
import pytest
from sqlmodel import Session, desc, select

from mvtool.data.projects import Projects
from mvtool.models.jira_ import JiraProject, JiraProjectImport
from mvtool.models.projects import Project, ProjectImport, ProjectInput
from mvtool.utils.errors import NotFoundError


def test_modify_projects_query_where_clause(session: Session, projects: Projects):
    # Create some test data
    projects.create_project(ProjectInput(name="apple"))
    projects.create_project(ProjectInput(name="banana"))
    projects.create_project(ProjectInput(name="cherry"))

    # Test filtering with a single where clause
    where_clauses = [Project.name == "banana"]
    query = projects._modify_projects_query(select(Project), where_clauses)
    results: list[Project] = session.exec(query).all()

    # Check the results
    assert len(results) == 1
    assert results[0].name == "banana"


def test_modify_projects_query_order_by(session: Session, projects: Projects):
    # Create some test data
    projects.create_project(ProjectInput(name="apple"))
    projects.create_project(ProjectInput(name="banana"))
    projects.create_project(ProjectInput(name="cherry"))

    # Test ordering
    order_by_clauses = [desc(Project.name)]
    query = projects._modify_projects_query(
        select(Project), order_by_clauses=order_by_clauses
    )
    results: list[Project] = session.exec(query).all()

    # Check the results
    assert [r.name for r in results] == ["cherry", "banana", "apple"]


def test_modify_projects_query_offset(session: Session, projects: Projects):
    # Create some test data
    projects.create_project(ProjectInput(name="apple"))
    projects.create_project(ProjectInput(name="banana"))
    projects.create_project(ProjectInput(name="cherry"))

    # Test offset
    query = projects._modify_projects_query(select(Project), offset=1)
    results: list[Project] = session.exec(query).all()

    # Check the results
    assert len(results) == 2


def test_modify_projects_query_limit(session: Session, projects: Projects):
    # Create some test data
    projects.create_project(ProjectInput(name="apple"))
    projects.create_project(ProjectInput(name="banana"))
    projects.create_project(ProjectInput(name="cherry"))

    # Test limit
    query = projects._modify_projects_query(select(Project), limit=2)
    results: list[Project] = session.exec(query).all()

    # Check the results
    assert len(results) == 2


def test_list_projects(projects: Projects):
    # Create some test data
    projects.create_project(ProjectInput(name="apple"))
    projects.create_project(ProjectInput(name="banana"))
    projects.create_project(ProjectInput(name="cherry"))

    # Test listing projects without querying Jira
    results = list(projects.list_projects(query_jira=False))
    assert len(results) == 3


def test_list_projects_query_jira(projects: Projects, jira_project_data: jira.Project):
    # Create some test data
    jp_id = jira_project_data.id
    projects.create_project(ProjectInput(name="apple", jira_project_id=jp_id))
    projects.create_project(ProjectInput(name="banana", jira_project_id=jp_id))
    projects.create_project(ProjectInput(name="cherry", jira_project_id=jp_id))

    # Test listing projects with querying Jira
    results = list(projects.list_projects(query_jira=True))
    assert len(results) == 3
    for result in results:
        assert result.jira_project_id == jp_id
        assert result.jira_project is not None


def test_count_projects(projects: Projects):
    # Create some test data
    projects.create_project(ProjectInput(name="apple"))
    projects.create_project(ProjectInput(name="banana"))
    projects.create_project(ProjectInput(name="cherry"))

    # Test counting projects without any filters
    count = projects.count_projects()
    assert count == 3


def test_create_project_from_project_input(projects: Projects):
    # Test creating a project from a ProjectInput
    project_input = ProjectInput(name="apple")
    project = projects.create_project(project_input)

    # Check if the project is created with the correct data
    assert project.id is not None
    assert project.name == project_input.name


def test_create_project_from_project_input_with_invalid_jira_project_id(
    projects: Projects,
):
    # Create a ProjectInput with an invalid Jira project ID
    project_input = ProjectInput(name="apple", jira_project_id="invalid")

    # Test creating a project from a ProjectInput with an invalid Jira project ID
    with pytest.raises(jira.JIRAError) as excinfo:
        projects.create_project(project_input)
        assert excinfo.value.status_code == 404


def test_create_project_from_project_import(
    projects: Projects, jira_project_data: jira.Project
):
    # Test creating a project with ProjectImport
    project_import = ProjectImport(
        id=-1, name="banana", jira_project=JiraProjectImport(key=jira_project_data.key)
    )
    project = projects.create_project(project_import)

    # Check if the project is created with the correct data
    assert project.id is not None
    assert project.name == project_import.name

    # Check if ignored fields are not changed
    assert project.id != project_import.id
    assert project.jira_project is None


def test_create_project_skip_flush(projects: Projects):
    project_input = ProjectInput(name="cherry")
    projects._session = Mock(wraps=projects._session)

    # Test creating a project without flushing the session
    projects.create_project(project_input, skip_flush=True)

    # Check if the session is not flushed
    projects._session.flush.assert_not_called()


def test_get_project(projects: Projects):
    # Create a project using the create_project method
    project_input = ProjectInput(name="apple")
    created_project = projects.create_project(project_input)

    # Retrieve the project using the get_project method
    result = projects.get_project(created_project.id)

    # Check if the correct project is returned
    assert created_project.id == result.id


def test_get_project_not_found(projects: Projects):
    # Test getting a project that does not exist
    with pytest.raises(NotFoundError):
        projects.get_project(-1)


def test_update_project_from_project_input(projects: Projects):
    # Create a project using the create_project method
    project_input = ProjectInput(name="old_name")
    project = projects.create_project(project_input)

    # Test updating the project with ProjectInput
    new_project_input = ProjectInput(name="new_name")
    projects.update_project(project, new_project_input)

    assert project.name == new_project_input.name


def test_update_project_with_invalid_jira_project_id(
    projects: Projects,
):
    # Create a project using the create_project method
    project_input = ProjectInput(name="apple")
    project = projects.create_project(project_input)

    # Update the project with an invalid Jira project ID
    updated_project_input = ProjectInput(name="banana", jira_project_id="invalid")

    # Test updating a project with an invalid Jira project ID
    with pytest.raises(jira.JIRAError) as excinfo:
        projects.update_project(project, updated_project_input)
        assert excinfo.value.status_code == 404


def test_update_project_from_project_import(
    projects: Projects, jira_project_data: jira.Project
):
    # Create a project
    project_input = ProjectInput(name="old_name")
    project = projects.create_project(project_input)

    # Test updating the project with ProjectImport
    new_project_import = ProjectImport(
        id=-1,
        name="new_name",
        jira_project=JiraProjectImport(key=jira_project_data.key),
    )
    old_project_id = project.id
    projects.update_project(project, new_project_import)

    # Check if the project is updated with the correct data
    assert project.name == new_project_import.name

    # Check if ignored fields are not changed
    assert project.id == old_project_id
    assert project.jira_project is None


def test_update_project_skip_flush(projects: Projects):
    # Create a project using the create_project method
    project_input = ProjectInput(name="name")
    project = projects.create_project(project_input)

    projects._session = Mock(wraps=projects._session)

    # Test updating the project with skip_flush=True
    projects.update_project(project, project_input, skip_flush=True)

    # Check if the flush method was not called
    projects._session.flush.assert_not_called()


def test_update_project_patch(projects: Projects):
    # Create a project using the create_project method
    old_project_input = ProjectInput(name="old_name")
    project = projects.create_project(old_project_input)

    # Test updating the project with patch=True
    new_project_input = ProjectInput(name="new_name")
    projects.update_project(project, new_project_input, patch=True)

    assert project.name == new_project_input.name


def test_delete_project(projects: Projects):
    # Create a project using the create_project method
    project_input = ProjectInput(name="test_project")
    created_project = projects.create_project(project_input)

    # Delete the project using the delete_project method
    projects.delete_project(created_project)

    # Check if the project is deleted
    with pytest.raises(NotFoundError):
        projects.get_project(created_project.id)


def test_delete_project_skip_flush(projects: Projects):
    # Create a project using the create_project method
    project_input = ProjectInput(name="test_project")
    created_project = projects.create_project(project_input)

    projects._session = Mock(wraps=projects._session)

    # Test deleting the project with skip_flush=True
    projects.delete_project(created_project, skip_flush=True)

    # Check if the flush method was not called
    projects._session.flush.assert_not_called()


def test_bulk_create_update_projects_create(projects: Projects):
    # Create some test data
    project_imports = [
        ProjectImport(name="name1"),
        ProjectImport(name="name2"),
    ]

    # Test creating projects
    created_projects = list(projects.bulk_create_update_projects(project_imports))

    # Check if the projects are created with the correct data
    assert len(created_projects) == 2
    for import_, created in zip(project_imports, created_projects):
        assert created.id is not None
        assert created.name == import_.name


@pytest.mark.parametrize("patch", [True, False])  # To archive branch coverage
def test_bulk_create_update_projects_update(projects: Projects, patch: bool):
    # Create projects to update
    project_input1 = ProjectInput(name="name1")
    project_input2 = ProjectInput(name="name2")
    created_project1 = projects.create_project(project_input1)
    created_project2 = projects.create_project(project_input2)

    # Update projects using bulk_create_update_projects
    project_imports = [
        ProjectImport(id=created_project1.id, name="new_name1"),
        ProjectImport(id=created_project2.id, name="new_name2"),
    ]

    updated_projects = list(
        projects.bulk_create_update_projects(project_imports, patch=patch)
    )

    assert len(updated_projects) == 2
    for import_, updated in zip(project_imports, updated_projects):
        assert updated.id == import_.id
        assert updated.name == import_.name


def test_bulk_create_update_projects_not_found_error(projects: Projects):
    project_imports = [ProjectImport(id=-1, name="name1")]

    with pytest.raises(NotFoundError):
        list(projects.bulk_create_update_projects(project_imports))


def test_bulk_create_update_projects_with_valid_jira_project_key(
    projects: Projects, jira_project_data: jira.Project
):
    # Create test data containing a valid Jira project key
    project_imports = [
        ProjectImport(
            name="name1", jira_project=JiraProjectImport(key=jira_project_data.key)
        )
    ]

    # Test creating a project with a valid Jira project key
    created_projects = list(projects.bulk_create_update_projects(project_imports))

    # Check if the project is created with the correct Jira project key
    assert len(created_projects) == 1
    assert created_projects[0].jira_project.key == jira_project_data.key


def test_bulk_create_update_projects_with_invalid_jira_project_key(projects: Projects):
    # Create test data containing an invalid Jira project key
    project_imports = [
        ProjectImport(name="name1", jira_project=JiraProjectImport(key="invalid"))
    ]

    # Test creating a project with an invalid Jira project key
    with pytest.raises(NotFoundError):
        list(projects.bulk_create_update_projects(project_imports))


def test_bulk_create_update_projects_skip_flush(projects: Projects):
    project_imports = [ProjectImport(name="name1")]
    projects._session = Mock(wraps=projects._session)

    # Test creating projects with skip_flush=True
    list(projects.bulk_create_update_projects(project_imports, skip_flush=True))

    # Check if the flush method was not called
    projects._session.flush.assert_not_called()


def test_convert_project_imports(projects: Projects):
    project_imports = [
        ProjectImport(name="name1"),
        ProjectImport(name="name2"),
    ]

    # Test converting project imports to projects
    project_map = projects.convert_project_imports(project_imports)

    # Check if the projects have the correct values
    assert len(project_map) == 2
    for project_import in project_imports:
        project = project_map[project_import.etag]
        assert project.name == project_import.name
