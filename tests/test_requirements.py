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

from mvtool.database import CRUDOperations
from mvtool.models import Requirement
from mvtool.views.projects import ProjectsView
from mvtool.views.requirements import RequirementsView

def test_list_requirements(
        projects_view: ProjectsView, crud: CRUDOperations, requirement):
    project_id = 1
    crud.read_all_from_db.return_value = [requirement]

    sut = RequirementsView(projects_view, crud)
    results = list(sut.list_requirements(project_id))

    assert isinstance(results[0], Requirement)
    assert results[0].id == requirement.id
    crud.read_all_from_db.assert_called_with(Requirement, project_id=project_id)

def test_create_requirement(
        projects_view: ProjectsView, crud: CRUDOperations, requirement_input, requirement, project):
    projects_view.get_project.return_value = project
    crud.create_in_db.return_value = requirement

    sut = RequirementsView(projects_view, crud)
    result = sut.create_requirement(project.id, requirement_input)

    assert isinstance(result, Requirement)
    result = crud.create_in_db.call_args[0][0]
    assert result.project == project

def test_get_requirement(
        projects_view: ProjectsView, crud: CRUDOperations, requirement):
    crud.read_from_db.return_value = requirement

    sut = RequirementsView(projects_view, crud)
    result = sut.get_requirement(requirement.id)

    assert isinstance(result, Requirement)
    crud.read_from_db.assert_called_with(Requirement, requirement.id)

def test_update_requirement(
        projects_view: ProjectsView, crud: CRUDOperations, requirement_input, requirement, project):
    requirement.project_id = project.id
    crud.read_from_db.return_value = requirement
    crud.update_in_db.return_value = requirement

    sut = RequirementsView(projects_view, crud)
    result = sut.update_requirement(project.id, requirement_input)

    assert isinstance(result, Requirement)
    result = crud.update_in_db.call_args[0][1]
    assert result.project_id == project.id

def test_delete_requirement(
        projects_view: ProjectsView, crud: CRUDOperations, requirement):
    crud.delete_from_db.return_value = None

    sut = RequirementsView(projects_view, crud)
    result = sut.delete_requirement(requirement.id)

    assert result is None
    crud.delete_from_db.assert_called_with(Requirement, requirement.id)