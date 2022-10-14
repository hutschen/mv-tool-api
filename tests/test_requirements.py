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
from mvtool.models import (
    CatalogModule,
    Measure,
    Project,
    Requirement,
    RequirementInput,
    RequirementOutput,
)
from mvtool.views.requirements import RequirementsView


def test_list_requirement_outputs(
    requirements_view: RequirementsView,
    create_project: Project,
    create_requirement: Requirement,
):
    results = list(requirements_view._list_requirements(create_project.id))

    assert len(results) == 1
    requirement_output = results[0]
    assert isinstance(requirement_output, RequirementOutput)
    assert requirement_output.id == create_requirement.id
    assert requirement_output.project.id == create_project.id


def test_list_catalog_requirement_outputs(
    requirements_view: RequirementsView,
    create_catalog_module: CatalogModule,
    create_catalog_requirement: Requirement,
    create_requirement: Requirement,
):
    results = list(
        requirements_view._list_catalog_requirements(create_catalog_module.id)
    )
    assert len(results) == 1
    requirement_output = results[0]
    assert isinstance(requirement_output, RequirementOutput)
    assert requirement_output.id == create_catalog_requirement.id
    assert requirement_output.project == None
    assert requirement_output.catalog_module.id == create_catalog_module.id


def test_create_requirement_output(
    requirements_view: RequirementsView,
    create_project: Project,
    requirement_input: RequirementInput,
):
    requirement_output = requirements_view._create_requirement(
        create_project.id, requirement_input
    )

    assert isinstance(requirement_output, RequirementOutput)
    assert requirement_output.summary == requirement_input.summary
    assert requirement_output.project.id == create_project.id
    assert requirement_output.catalog_module == None


def test_create_requirement_output_invalid_project_id(
    requirements_view: RequirementsView, requirement_input: RequirementInput
):
    with pytest.raises(HTTPException) as excinfo:
        requirements_view._create_requirement(-1, requirement_input)
    excinfo.value.status_code == 404


def test_create_catalog_requirement_output(
    requirements_view: RequirementsView,
    create_catalog_module: CatalogModule,
    requirement_input: RequirementInput,
):
    requirement_output = requirements_view._create_catalog_requirement(
        create_catalog_module.id, requirement_input
    )
    assert isinstance(requirement_output, RequirementOutput)
    assert requirement_output.summary == requirement_input.summary
    assert requirement_output.project == None
    assert requirement_output.catalog_module.id == create_catalog_module.id


def test_create_catalog_requirement_output_invalid_catalog_module_id(
    requirements_view: RequirementsView, requirement_input: RequirementInput
):
    with pytest.raises(HTTPException) as excinfo:
        requirements_view._create_catalog_requirement(-1, requirement_input)
    excinfo.value.status_code == 404


def test_get_requirement_output(
    requirements_view: RequirementsView, create_requirement: Requirement
):
    requirement_output = requirements_view._get_requirement(create_requirement.id)

    assert isinstance(requirement_output, RequirementOutput)
    assert requirement_output.id == create_requirement.id
    assert requirement_output.project.id == create_requirement.project_id


def test_get_requirement_output_invalid_id(requirements_view: RequirementsView):
    with pytest.raises(HTTPException) as excinfo:
        requirements_view._get_requirement(-1)
        excinfo.value.status_code == 404


def test_update_requirement_output(
    requirements_view: RequirementsView,
    create_requirement: Requirement,
    requirement_input: RequirementInput,
):
    requirement_output = requirements_view._update_requirement(
        create_requirement.id, requirement_input
    )

    assert isinstance(requirement_output, RequirementOutput)
    assert requirement_output.id == create_requirement.id
    assert requirement_output.summary == requirement_input.summary
    assert requirement_output.project.id == create_requirement.project_id


def test_update_requirement_output_invalid_id(
    requirements_view: RequirementsView, requirement_input: RequirementInput
):
    with pytest.raises(HTTPException) as excinfo:
        requirements_view._update_requirement(-1, requirement_input)
        excinfo.value.status_code == 404


def test_delete_requirement(
    requirements_view: RequirementsView, create_requirement: Requirement
):
    requirements_view.delete_requirement(create_requirement.id)

    with pytest.raises(HTTPException) as excinfo:
        requirements_view.delete_requirement(create_requirement.id)
        excinfo.value.status_code == 404


def test_requirement_completion_incomplete(create_requirement: Requirement):
    assert create_requirement.completion == 0.0


def test_requirement_completion_complete(
    create_requirement: Requirement, create_measure: Measure
):
    create_measure.completed = True
    assert create_requirement.completion == 1.0


def test_requirement_compleation_ignored(create_requirement: Requirement):
    create_requirement.compliance_status = "NC"
    assert create_requirement.completion == None
