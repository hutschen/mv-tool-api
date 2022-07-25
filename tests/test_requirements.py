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
from fastapi import HTTPException
from mvtool.models import Project, Requirement, RequirementInput, RequirementOutput
from mvtool.views.requirements import RequirementsView

def test_list_requirement_outputs(
        requirements_view: RequirementsView, create_project: Project,
        create_requirement: Requirement):
    results = list(requirements_view._list_requirements(create_project.id))

    assert len(results) == 1
    requirement_output = results[0]
    assert isinstance(requirement_output, RequirementOutput)
    assert requirement_output.id == create_requirement.id
    assert requirement_output.project.id == create_project.id

def test_create_requirement_output(
        requirements_view: RequirementsView, create_project: Project, 
        requirement_input: RequirementInput):
    requirement_output = requirements_view._create_requirement(
        create_project.id, requirement_input)
    
    assert isinstance(requirement_output, RequirementOutput)
    assert requirement_output.summary == requirement_input.summary
    assert requirement_output.project.id == create_project.id
    
def test_create_requirement_output_invalid_project_id(
        requirements_view: RequirementsView, 
        requirement_input: RequirementInput):
    with pytest.raises(HTTPException) as excinfo:
        requirements_view._create_requirement(-1, requirement_input)
        excinfo.value.status_code == 404

def test_get_requirement_output(
        requirements_view: RequirementsView, create_requirement: Requirement):
    requirement_output = requirements_view._get_requirement(create_requirement.id)

    assert isinstance(requirement_output, RequirementOutput)
    assert requirement_output.id == create_requirement.id
    assert requirement_output.project.id == create_requirement.project_id

def test_get_requirement_output_invalid_id(requirements_view: RequirementsView):
    with pytest.raises(HTTPException) as excinfo:
        requirements_view._get_requirement(-1)
        excinfo.value.status_code == 404

def test_update_requirement_output(
        requirements_view: RequirementsView, create_requirement: Requirement,
        requirement_input: RequirementInput):
    requirement_output = requirements_view._update_requirement(
        create_requirement.id, requirement_input)

    assert isinstance(requirement_output, RequirementOutput)
    assert requirement_output.id == create_requirement.id
    assert requirement_output.summary == requirement_input.summary
    assert requirement_output.project.id == create_requirement.project_id

def test_update_requirement_output_invalid_id(
        requirements_view: RequirementsView, 
        requirement_input: RequirementInput):
    with pytest.raises(HTTPException) as excinfo:
        requirements_view._update_requirement(-1, requirement_input)
        excinfo.value.status_code == 404

def test_delete_requirement(
        requirements_view: RequirementsView,
        create_requirement: Requirement):
    requirements_view.delete_requirement(create_requirement.id)

    with pytest.raises(HTTPException) as excinfo:
        requirements_view.delete_requirement(create_requirement.id)
        excinfo.value.status_code == 404