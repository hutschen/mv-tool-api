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
    CatalogRequirement,
    Measure,
    Project,
    Requirement,
    RequirementInput,
)
from mvtool.handlers.catalog_requirements import CatalogRequirements
from mvtool.handlers.requirements import Requirements


def test_list_requirements(
    requirements_view: Requirements,
    create_project: Project,
    create_requirement: Requirement,
):
    results = requirements_view.list_requirements(
        Requirement.project_id == create_project.id
    )

    assert len(results) == 1
    requirement = results[0]
    assert isinstance(requirement, Requirement)
    assert requirement.id == create_requirement.id
    assert requirement.project.id == create_project.id
    assert requirement.project.jira_project.id == create_project.jira_project_id


def test_list_requirements_with_invalid_project_id(
    requirements_view: Requirements,
):
    results = requirements_view.list_requirements(Requirement.project_id == -1)
    assert len(results) == 0


def test_list_requirements_without_jira_project(
    requirements_view: Requirements,
    create_project: Project,
    create_requirement: Requirement,
):
    create_project.jira_project_id = None
    results = requirements_view.list_requirements(
        Requirement.project_id == create_project.id
    )

    assert len(results) == 1
    requirement = results[0]
    assert isinstance(requirement, Requirement)
    assert requirement.id == create_requirement.id
    assert requirement.project.jira_project == None


def test_create_requirement(
    requirements_view: Requirements,
    create_project: Project,
    requirement_input: RequirementInput,
):
    requirement = requirements_view.create_requirement(
        create_project, requirement_input
    )

    assert isinstance(requirement, Requirement)
    assert requirement.summary == requirement_input.summary
    assert requirement.project.id == create_project.id
    assert requirement.project.jira_project.id == create_project.jira_project_id


def test_create_requirement_without_catalog_requirement_id(
    requirements_view: Requirements,
    create_project: Project,
    requirement_input: RequirementInput,
):
    requirement_input.catalog_requirement_id = None
    requirement = requirements_view.create_requirement(
        create_project, requirement_input
    )

    assert isinstance(requirement, Requirement)
    assert requirement.summary == requirement_input.summary
    assert requirement.project.id == create_project.id
    assert requirement.project.jira_project.id == create_project.jira_project_id
    assert requirement.catalog_requirement == None


def test_create_requirement_with_invalid_catalog_requirement_id(
    requirements_view: Requirements,
    create_project: Project,
    requirement_input: RequirementInput,
):
    requirement_input.catalog_requirement_id = -1
    with pytest.raises(HTTPException) as excinfo:
        requirements_view.create_requirement(create_project, requirement_input)
    excinfo.value.status_code == 404


def test_get_requirement(
    requirements_view: Requirements,
    create_project: Project,
    create_requirement: Requirement,
):
    requirement = requirements_view.get_requirement(create_requirement.id)

    assert isinstance(requirement, Requirement)
    assert requirement.id == create_requirement.id
    assert requirement.project.id == create_requirement.project_id
    assert requirement.project.jira_project.id == create_project.jira_project_id


def test_get_requirement_with_invalid_id(requirements_view: Requirements):
    with pytest.raises(HTTPException) as excinfo:
        requirements_view.get_requirement(-1)
    excinfo.value.status_code == 404


def test_update_requirement(
    requirements_view: Requirements,
    create_requirement: Requirement,
    requirement_input: RequirementInput,
):
    orig_name = requirement_input.summary
    requirement_input.summary += " (updated)"
    requirements_view.update_requirement(create_requirement, requirement_input)

    assert create_requirement.summary != orig_name
    assert create_requirement.summary == requirement_input.summary


def test_delete_requirement(
    requirements_view: Requirements, create_requirement: Requirement
):
    requirements_view.delete_requirement(create_requirement)

    with pytest.raises(HTTPException) as excinfo:
        requirements_view.get_requirement(create_requirement.id)
    excinfo.value.status_code == 404


def test_bulk_create_requirements_from_catalog_requirements(
    requirements_view: Requirements,
    create_project: Project,
    create_catalog_requirement: CatalogRequirement,
):
    results = list(
        requirements_view.bulk_create_requirements_from_catalog_requirements(
            create_project, [create_catalog_requirement]
        )
    )

    assert len(results) == 1
    requirement = results[0]
    assert isinstance(requirement, Requirement)
    assert requirement.summary == create_catalog_requirement.summary
    assert requirement.project.id == create_project.id
    assert requirement.project.jira_project.id == create_project.jira_project_id
    assert requirement.catalog_requirement.id == create_catalog_requirement.id


def test_requirement_completion_progress_incomplete(create_requirement: Requirement):
    assert create_requirement.completion_progress == 0.0


def test_requirement_completion_progress_complete(
    create_requirement: Requirement, create_measure: Measure
):
    create_measure.completion_status = "completed"
    assert create_requirement.completion_progress == 1.0


def test_requirement_completion_progress_ignored(create_requirement: Requirement):
    create_requirement.compliance_status = "NC"
    assert create_requirement.completion_progress == None


def test_requirement_verification_progress_incomplete(create_requirement: Requirement):
    assert create_requirement.verification_progress == 0.0


def test_requirement_verification_progress_complete(
    create_requirement: Requirement, create_measure: Measure
):
    create_measure.verification_status = "verified"
    assert create_requirement.verification_progress == 1.0


def test_requirement_verification_progress_ignored(create_requirement: Requirement):
    create_requirement.compliance_status = "NC"
    assert create_requirement.verification_progress == None
