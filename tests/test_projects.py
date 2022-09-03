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

import pytest
from fastapi import HTTPException
from jira import JIRAError
from mvtool.models import Project, ProjectInput, ProjectOutput, Requirement, Measure
from mvtool.views.projects import ProjectsView


def test_list_project_outputs(projects_view: ProjectsView, create_project: Project):
    results = list(projects_view._list_projects())

    assert len(results) == 1
    project_output = results[0]
    assert isinstance(project_output, ProjectOutput)
    assert project_output.id == create_project.id
    assert project_output.jira_project.id == create_project.jira_project_id


def test_create_project_output_jira_project_id(
    projects_view: ProjectsView, project_input: ProjectInput
):
    assert project_input.jira_project_id is not None
    project_output = projects_view._create_project(project_input)

    assert isinstance(project_output, ProjectOutput)
    assert project_output.name == project_input.name
    assert project_output.jira_project.id == project_input.jira_project_id


def test_create_project_output_no_jira_project_id(
    projects_view: ProjectsView, project_input: ProjectInput
):
    project_input.jira_project_id = None
    project_output = projects_view._create_project(project_input)

    assert isinstance(project_output, ProjectOutput)
    assert project_output.name == project_input.name
    assert project_output.jira_project is None


def test_create_project_output_invalid_jira_project_id(
    projects_view: ProjectsView, project_input: ProjectInput
):
    project_input.jira_project_id = "invalid"
    with pytest.raises(JIRAError) as exception_info:
        projects_view._create_project(project_input)
        assert exception_info.value.status_code == 404


def test_get_project_output(projects_view: ProjectsView, create_project: Project):
    assert create_project.jira_project_id is not None
    project_output = projects_view._get_project(create_project.id)

    assert isinstance(project_output, ProjectOutput)
    assert project_output.id == create_project.id
    assert project_output.name == create_project.name
    assert project_output.jira_project.id == create_project.jira_project_id


def test_get_project_output_invalid_id(projects_view: ProjectsView):
    with pytest.raises(HTTPException) as exception_info:
        projects_view._get_project("invalid")
        assert exception_info.value.status_code == 404


def test_update_project_output(
    projects_view: ProjectsView, create_project: Project, project_input: ProjectInput
):
    assert create_project.jira_project_id is not None
    orig_name = project_input.name
    project_input.name += " (updated)"

    project_output = projects_view._update_project(create_project.id, project_input)

    assert isinstance(project_output, ProjectOutput)
    assert project_output.id == create_project.id
    assert project_output.name != orig_name
    assert project_output.name == project_input.name
    assert project_output.jira_project.id == project_input.jira_project_id


def test_update_project_output_invalid_jira_project_id(
    projects_view: ProjectsView, create_project: Project, project_input: ProjectInput
):
    project_input.jira_project_id = "invalid"
    with pytest.raises(JIRAError) as exception_info:
        projects_view._update_project(create_project.id, project_input)
        assert exception_info.value.status_code == 404


def test_update_project_output_invalid_id(
    projects_view: ProjectsView, project_input: ProjectInput
):
    with pytest.raises(HTTPException) as exception_info:
        projects_view._update_project("invalid", project_input)
        assert exception_info.value.status_code == 404


def test_delete_project(projects_view: ProjectsView, create_project: Project):
    projects_view.delete_project(create_project.id)

    with pytest.raises(HTTPException) as exception_info:
        projects_view.get_project(create_project.id)
        assert exception_info.value.status_code == 404


def test_project_completion_no_requirements(create_project: Project):
    assert create_project.completion == None


def test_project_completion_no_measures(
    create_project: Project, create_requirement: Requirement
):
    assert create_project.completion == 0.0


def test_project_completion_complete(
    create_project: Project,
    create_requirement: Requirement,
    create_measure: Measure,
):
    create_requirement.compliance_status = "C"
    create_measure.completed = True

    assert create_requirement.completion == 1.0
    assert create_project.completion == 1.0


def test_project_completion_incomplete(
    create_project: Project,
    create_requirement: Requirement,
    create_measure: Measure,
):
    create_requirement.compliance_status = "C"
    create_measure.completed = False

    assert create_requirement.completion == 0.0
    assert create_project.completion == 0.0
