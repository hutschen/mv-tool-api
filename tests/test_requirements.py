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

from unittest.mock import ANY
from mvtool.database import CRUDOperations
from mvtool.models import Project, ProjectOutput, Requirement, RequirementInput, RequirementOutput
from mvtool.views.projects import ProjectsView
from mvtool.views.requirements import RequirementsView

def test_list_requirements(
        projects_view: ProjectsView, 
        crud: CRUDOperations, requirement: Requirement):
    project_id = 1
    crud.read_all_from_db.return_value = [requirement]

    sut = RequirementsView(projects_view, crud)
    results = list(sut.list_requirements(project_id))

    assert isinstance(results[0], Requirement)
    assert results[0].id == requirement.id
    crud.read_all_from_db.assert_called_with(Requirement, project_id=project_id)

def test_list_requirement_outputs(
        projects_view: ProjectsView, crud: CRUDOperations, 
        requirement: Requirement, project_output: ProjectOutput):
    crud.read_all_from_db.return_value = [requirement]
    projects_view._get_project.return_value = project_output

    sut = RequirementsView(projects_view, crud)
    results = list(sut._list_requirements(project_output.id))

    assert isinstance(results[0], RequirementOutput)
    assert isinstance(results[0].project, ProjectOutput)
    projects_view._get_project.assert_called_with(project_output.id)

def test_create_requirement(
        projects_view: ProjectsView, crud: CRUDOperations, 
        requirement_input: RequirementInput, requirement: Requirement, 
        project: Project):
    projects_view.get_project.return_value = project
    crud.create_in_db.return_value = requirement

    sut = RequirementsView(projects_view, crud)
    result = sut.create_requirement(project.id, requirement_input)

    assert isinstance(result, Requirement)
    result = crud.create_in_db.call_args[0][0]
    assert result.project == project

def test_create_requirement_output(
        projects_view: ProjectsView, crud: CRUDOperations, 
        requirement_input: RequirementInput, 
        requirement: Requirement, project: Project, 
        project_output: ProjectOutput):
    projects_view.get_project.return_value = project
    projects_view._get_project.return_value = project_output
    crud.create_in_db.return_value = requirement

    sut = RequirementsView(projects_view, crud)
    result = sut._create_requirement(project_output.id, requirement_input)

    assert isinstance(result, RequirementOutput)
    assert isinstance(result.project, ProjectOutput)
    projects_view._get_project.assert_called_with(project_output.id)

def test_get_requirement(
        projects_view: ProjectsView, crud: CRUDOperations, requirement):
    crud.read_from_db.return_value = requirement

    sut = RequirementsView(projects_view, crud)
    result = sut.get_requirement(requirement.id)

    assert isinstance(result, Requirement)
    crud.read_from_db.assert_called_with(Requirement, requirement.id)

def test_get_requirement_output(
        projects_view: ProjectsView, crud: CRUDOperations, 
        requirement: Requirement, project: Project, 
        project_output: ProjectOutput):
    crud.read_from_db.return_value = requirement
    projects_view.get_project.return_value = project
    projects_view._get_project.return_value = project_output

    sut = RequirementsView(projects_view, crud)
    result = sut._get_requirement(requirement.id)

    assert isinstance(result, RequirementOutput)
    assert isinstance(result.project, ProjectOutput)
    projects_view._get_project.assert_called_with(project_output.id)

def test_update_requirement(
        projects_view: ProjectsView, crud: CRUDOperations, 
        requirement_input: RequirementInput, requirement: Requirement):
    crud.read_from_db.return_value = requirement
    crud.update_in_db.return_value = requirement

    sut = RequirementsView(projects_view, crud)
    result = sut.update_requirement(requirement.project_id, requirement_input)

    assert isinstance(result, Requirement)
    crud.update_in_db.assert_called_with(requirement.id, ANY)

def test_update_requirement_output(
        projects_view: ProjectsView, crud: CRUDOperations, 
        requirement_input: RequirementInput, requirement: Requirement, 
        project: Project, project_output: ProjectOutput):
    crud.read_from_db.return_value = requirement
    crud.update_in_db.return_value = requirement
    projects_view.get_project.return_value = project
    projects_view._get_project.return_value = project_output

    sut = RequirementsView(projects_view, crud)
    result = sut._update_requirement(requirement.id, requirement_input)

    assert isinstance(result, RequirementOutput)
    assert isinstance(result.project, ProjectOutput)
    projects_view._get_project.assert_called_with(project_output.id)

def test_delete_requirement(
        projects_view: ProjectsView, crud: CRUDOperations, requirement):
    crud.delete_from_db.return_value = None

    sut = RequirementsView(projects_view, crud)
    result = sut.delete_requirement(requirement.id)

    assert result is None
    crud.delete_from_db.assert_called_with(Requirement, requirement.id)