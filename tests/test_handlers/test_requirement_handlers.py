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

import pytest
from mvtool.data.catalog_requirements import CatalogRequirements
from mvtool.data.requirements import Requirements
from mvtool.data.projects import Projects
from mvtool.handlers.requirements import (
    get_requirements,
    create_requirement,
    get_requirement,
    update_requirement,
    delete_requirement,
    import_requirements_from_catalog_modules,
    get_requirement_representations,
    get_requirement_field_names,
    _create_requirement_field_values_handler,
)
from mvtool.models.catalog_modules import CatalogModule
from mvtool.models.catalog_requirements import CatalogRequirement
from mvtool.models.requirements import (
    Requirement,
    RequirementInput,
    RequirementOutput,
    RequirementRepresentation,
)
from mvtool.models.projects import Project
from mvtool.utils.pagination import Page


def test_get_requirements_list(requirements: Requirements):
    requirements_list = get_requirements([], [], {}, requirements)

    assert isinstance(requirements_list, list)
    for requirement in requirements_list:
        assert isinstance(requirement, Requirement)


def test_get_requirements_with_pagination(
    requirements: Requirements, requirement: Requirement
):
    page_params = dict(offset=0, limit=1)
    requirements_page = get_requirements([], [], page_params, requirements)

    assert isinstance(requirements_page, Page)
    assert requirements_page.total_count == 1
    for requirement_ in requirements_page.items:
        assert isinstance(requirement_, RequirementOutput)


def test_create_requirement(
    projects: Projects, requirements: Requirements, project: Project
):
    project_id = project.id
    requirement_input = RequirementInput(
        summary="Example Requirement", project_id=project_id
    )
    created_requirement = create_requirement(
        project_id, requirement_input, projects, requirements
    )

    assert isinstance(created_requirement, Requirement)
    assert created_requirement.summary == requirement_input.summary
    assert created_requirement.project_id == project_id


def test_get_requirement(requirements: Requirements, requirement: Requirement):
    requirement_id = requirement.id
    retrieved_requirement = get_requirement(requirement_id, requirements)

    assert isinstance(retrieved_requirement, Requirement)
    assert retrieved_requirement.id == requirement_id


def test_update_requirement(requirements: Requirements, requirement: Requirement):
    requirement_id = requirement.id
    requirement_input = RequirementInput(summary="Updated Requirement")
    updated_requirement = update_requirement(
        requirement_id, requirement_input, requirements
    )

    assert isinstance(updated_requirement, Requirement)
    assert updated_requirement.id == requirement_id
    assert updated_requirement.summary == requirement_input.summary


def test_delete_requirement(requirements: Requirements, requirement: Requirement):
    requirement_id = requirement.id
    delete_requirement(requirement_id, requirements)

    with pytest.raises(Exception):
        # Check if the requirement was deleted
        get_requirement(requirement_id, requirements)


def test_import_requirements_from_catalog_modules(
    projects: Projects,
    catalog_requirements: CatalogRequirements,
    requirements: Requirements,
    project: Project,
    catalog_module: CatalogModule,
    catalog_requirement: CatalogRequirement,
):
    catalog_module_ids = [catalog_module.id]
    imported_requirements = list(
        import_requirements_from_catalog_modules(
            project.id,
            catalog_module_ids,
            projects,
            catalog_requirements,
            requirements,
        )
    )

    assert len(imported_requirements) == 1
    assert imported_requirements[0].catalog_requirement_id == catalog_requirement.id


def test_get_requirement_representations_list(
    requirements: Requirements, requirement: Requirement
):
    results = get_requirement_representations([], None, [], {}, requirements)

    assert isinstance(results, list)
    for item in results:
        assert isinstance(item, Requirement)


def test_get_requirement_representations_with_pagination(
    requirements: Requirements, requirement: Requirement
):
    page_params = dict(offset=0, limit=1)
    resulting_page = get_requirement_representations(
        [], None, [], page_params, requirements
    )

    assert isinstance(resulting_page, Page)
    assert resulting_page.total_count == 1
    for item in resulting_page.items:
        assert isinstance(item, RequirementRepresentation)


def test_get_requirement_representations_local_search(
    requirements: Requirements, project: Project
):
    # Create two requirements with different summaries
    requirement_inputs = [
        RequirementInput(reference="apples", summary="apples_summary"),
        RequirementInput(reference="bananas", summary="bananas_summary"),
    ]
    for requirement_input in requirement_inputs:
        requirements.create_requirement(project, requirement_input)

    # Get representations using local_search to filter the requirements
    local_search = "bananas"
    representations = get_requirement_representations(
        [], local_search, [], {}, requirements
    )

    # Check if the correct requirement is returned after filtering
    assert isinstance(representations, list)
    assert len(representations) == 1
    requirement = representations[0]
    assert isinstance(requirement, Requirement)
    assert requirement.reference == "bananas"
    assert requirement.summary == "bananas_summary"


def test_get_requirement_field_names_default_list(requirements: Requirements):
    field_names = get_requirement_field_names([], requirements)

    assert isinstance(field_names, set)
    assert field_names == {"id", "summary", "project"}


def test_get_requirement_field_names_full_list(
    requirements: Requirements,
    project: Project,
    catalog_requirement: CatalogRequirement,
):
    # Create a requirement to get all fields
    requirement_input = RequirementInput(
        reference="reference",
        summary="summary",
        description="description",
        target_object="target object",
        milestone="milestone",
        compliance_status="C",
        compliance_comment="compliance comment",
        catalog_requirement_id=catalog_requirement.id,
    )
    requirements.create_requirement(project, requirement_input)

    field_names = get_requirement_field_names([], requirements)

    # Check if all field names are returned
    assert isinstance(field_names, set)
    assert field_names == {
        "id",
        "summary",
        "project",
        "reference",
        "description",
        "target_object",
        "milestone",
        "compliance_status",
        "compliance_comment",
        "catalog_requirement",
        "catalog_module",
        "catalog",
    }


get_requirement_references = _create_requirement_field_values_handler(
    Requirement.reference
)


def test_get_requirement_references_list(requirements: Requirements, project: Project):
    # Create a requirement with a reference
    requirement_input = RequirementInput(reference="reference", summary="summary")
    requirements.create_requirement(project, requirement_input)

    # Get references without pagination
    references = get_requirement_references([], None, {}, requirements)

    # Check if all references are returned
    assert isinstance(references, list)
    assert references == ["reference"]


def test_get_requirement_references_with_pagination(
    requirements: Requirements, project: Project
):
    # Create a requirement with a reference
    requirement_input = RequirementInput(reference="reference", summary="summary")
    requirements.create_requirement(project, requirement_input)

    # Get references with pagination
    page_params = dict(offset=0, limit=1)
    references_page = get_requirement_references([], None, page_params, requirements)

    # Check if the correct reference is returned
    assert isinstance(references_page, Page)
    assert references_page.total_count == 1
    assert references_page.items == ["reference"]


def test_get_requirement_references_local_search(
    requirements: Requirements, project: Project
):
    # Create two requirements with different references
    requirement_inputs = [
        RequirementInput(reference="apples", summary="apples_summary"),
        RequirementInput(reference="bananas", summary="bananas_summary"),
    ]
    for requirement_input in requirement_inputs:
        requirements.create_requirement(project, requirement_input)

    # Get references using local_search to filter the requirements
    local_search = "bananas"
    references = get_requirement_references([], local_search, {}, requirements)

    # Check if the correct reference is returned after filtering
    assert isinstance(references, list)
    assert references == ["bananas"]
