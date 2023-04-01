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
from mvtool.models import Project, ProjectInput, Requirement, Measure
from mvtool.handlers.projects import ProjectsView


def test_list_project(projects_view: ProjectsView, create_project: Project):
    results = list(projects_view.list_projects())

    assert len(results) == 1
    project = results[0]
    assert isinstance(project, Project)
    assert project.id == create_project.id
    assert project.jira_project.id == create_project.jira_project_id


def test_create_project_with_jira_project_id(
    projects_view: ProjectsView, project_input: ProjectInput
):
    assert project_input.jira_project_id is not None
    project = projects_view.create_project(project_input)

    assert isinstance(project, Project)
    assert project.name == project_input.name
    assert project.jira_project.id == project_input.jira_project_id


def test_create_project_without_jira_project_id(
    projects_view: ProjectsView, project_input: ProjectInput
):
    project_input.jira_project_id = None
    project = projects_view.create_project(project_input)

    assert isinstance(project, Project)
    assert project.name == project_input.name
    assert project.jira_project is None


def test_create_project_with_invalid_jira_project_id(
    projects_view: ProjectsView, project_input: ProjectInput
):
    project_input.jira_project_id = "invalid"
    with pytest.raises(JIRAError) as exception_info:
        projects_view.create_project(project_input)
        assert exception_info.value.status_code == 404


def test_get_project(projects_view: ProjectsView, create_project: Project):
    assert create_project.jira_project_id is not None
    project = projects_view.get_project(create_project.id)

    assert isinstance(project, Project)
    assert project.id == create_project.id
    assert project.name == create_project.name
    assert project.jira_project.id == create_project.jira_project_id


def test_get_project_using_an_invalid_id(projects_view: ProjectsView):
    with pytest.raises(HTTPException) as exception_info:
        projects_view.get_project("invalid")
        assert exception_info.value.status_code == 404


def test_update_project(
    projects_view: ProjectsView, create_project: Project, project_input: ProjectInput
):
    assert create_project.jira_project_id is not None
    orig_name = project_input.name
    project_input.name += " (updated)"

    projects_view.update_project(create_project, project_input)

    assert create_project.name != orig_name
    assert create_project.name == project_input.name
    assert create_project.jira_project.id == project_input.jira_project_id


def test_update_project_with_invalid_jira_project_id(
    projects_view: ProjectsView, create_project: Project, project_input: ProjectInput
):
    project_input.jira_project_id = "invalid"
    with pytest.raises(JIRAError) as exception_info:
        projects_view.update_project(create_project, project_input)
        assert exception_info.value.status_code == 404


def test_delete_project(projects_view: ProjectsView, create_project: Project):
    projects_view.delete_project(create_project)

    with pytest.raises(HTTPException) as exception_info:
        projects_view.get_project(create_project.id)
        assert exception_info.value.status_code == 404


def test_project_jira_project_without_getter():
    project = Project(name="test", jira_project_id="test")
    with pytest.raises(AttributeError):
        project.jira_project


def test_project_jira_project_with_getter():
    jira_project_dummy = object()
    project = Project(name="test", jira_project_id="test")
    project._get_jira_project = lambda _: jira_project_dummy
    assert project.jira_project is jira_project_dummy


def test_project_completion_progress_no_requirements(create_project: Project):
    assert create_project.completion_progress == None


def test_project_completion_progress_no_measures(
    create_project: Project, create_requirement: Requirement
):
    assert create_project.completion_progress == 0.0


def test_project_completion_progress_nothing_to_complete(
    create_project: Project, create_requirement: Requirement
):
    create_requirement.compliance_status = "NC"

    assert create_requirement.completion_progress == None
    assert create_project.completion_progress == None


def test_project_completion_progress_complete(
    create_project: Project,
    create_requirement: Requirement,
    create_measure: Measure,
):
    create_requirement.compliance_status = "C"
    create_measure.completion_status = "completed"

    assert create_requirement.completion_progress == 1.0
    assert create_project.completion_progress == 1.0


def test_project_completion_progress_incomplete(
    create_project: Project,
    create_requirement: Requirement,
    create_measure: Measure,
):
    create_requirement.compliance_status = "C"
    create_measure.completion_status = "open"

    assert create_requirement.completion_progress == 0.0
    assert create_project.completion_progress == 0.0


def test_project_verification_progress_no_requirements(create_project: Project):
    assert create_project.verification_progress == None


def test_project_verification_progress_no_measures(
    create_project: Project, create_requirement: Requirement
):
    assert create_project.verification_progress == 0.0


def test_project_verification_progress_nothing_to_verify(
    create_project: Project, create_requirement: Requirement
):
    create_requirement.compliance_status = "NC"

    assert create_requirement.verification_progress == None
    assert create_project.verification_progress == None


def test_project_verification_progress_verified(
    create_project: Project,
    create_requirement: Requirement,
    create_measure: Measure,
):
    create_requirement.compliance_status = "C"
    create_measure.verification_status = "verified"

    assert create_requirement.verification_progress == 1.0
    assert create_project.verification_progress == 1.0


def test_project_verification_progress_unverified(
    create_project: Project,
    create_requirement: Requirement,
    create_measure: Measure,
):
    create_requirement.compliance_status = "C"
    create_measure.verification_status = "not verified"

    assert create_requirement.verification_progress == 0.0
    assert create_project.verification_progress == 0.0
