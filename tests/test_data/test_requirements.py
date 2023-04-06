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

import pytest
from sqlmodel import Session, desc, select

from mvtool.data.requirements import Requirements
from mvtool.models.catalog_modules import CatalogModule
from mvtool.models.catalog_requirements import (
    CatalogRequirement,
    CatalogRequirementImport,
)
from mvtool.models.projects import Project, ProjectImport
from mvtool.models.requirements import Requirement, RequirementImport, RequirementInput
from mvtool.utils.errors import NotFoundError, ValueHttpError


def test_modify_requirements_query_where_clause(
    session: Session, requirements: Requirements, project: Project
):
    # Create some test data
    requirement_inputs = [
        RequirementInput(reference="apple", summary="Apple"),
        RequirementInput(reference="banana", summary="Banana"),
        RequirementInput(reference="cherry", summary="Cherry"),
    ]
    for requirement_input in requirement_inputs:
        requirements.create_requirement(project, requirement_input)

    # Test filtering with a single where clause
    where_clauses = [Requirement.reference == "banana"]
    query = requirements._modify_requirements_query(select(Requirement), where_clauses)
    results: list[Requirement] = session.exec(query).all()
    assert len(results) == 1
    assert results[0].reference == "banana"


def test_modify_requirements_query_order_by(
    session: Session, requirements: Requirements, project: Project
):
    # Create some test data
    requirement_inputs = [
        RequirementInput(reference="apple", summary="Apple"),
        RequirementInput(reference="banana", summary="Banana"),
        RequirementInput(reference="cherry", summary="Cherry"),
    ]
    for requirement_input in requirement_inputs:
        requirements.create_requirement(project, requirement_input)

    # Test ordering
    order_by_clauses = [desc(Requirement.reference)]
    query = requirements._modify_requirements_query(
        select(Requirement), order_by_clauses=order_by_clauses
    )
    results = session.exec(query).all()
    assert [r.reference for r in results] == ["cherry", "banana", "apple"]


def test_modify_requirements_query_offset(
    session: Session, requirements: Requirements, project: Project
):
    # Create some test data
    requirement_inputs = [
        RequirementInput(reference="apple", summary="Apple"),
        RequirementInput(reference="banana", summary="Banana"),
        RequirementInput(reference="cherry", summary="Cherry"),
    ]
    for requirement_input in requirement_inputs:
        requirements.create_requirement(project, requirement_input)

    # Test offset
    query = requirements._modify_requirements_query(select(Requirement), offset=2)
    results = session.exec(query).all()
    assert len(results) == 1


def test_modify_requirements_query_limit(
    session: Session, requirements: Requirements, project: Project
):
    # Create some test data
    requirement_inputs = [
        RequirementInput(reference="apple", summary="Apple"),
        RequirementInput(reference="banana", summary="Banana"),
        RequirementInput(reference="cherry", summary="Cherry"),
    ]
    for requirement_input in requirement_inputs:
        requirements.create_requirement(project, requirement_input)

    # Test limit
    query = requirements._modify_requirements_query(select(Requirement), limit=1)
    results = session.exec(query).all()
    assert len(results) == 1


def test_list_requirements(requirements: Requirements, project: Project):
    # Create some test data
    requirement_inputs = [
        RequirementInput(reference="apple", summary="apple_summary"),
        RequirementInput(reference="banana", summary="banana_summary"),
        RequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for requirement_input in requirement_inputs:
        requirements.create_requirement(project, requirement_input)

    # Test listing requirements without any filters
    results = requirements.list_requirements(query_jira=False)
    assert len(results) == len(requirement_inputs)


def test_list_requirements_query_jira(requirements: Requirements, project: Project):
    # Create some test data
    requirement_input = RequirementInput(reference="reference", summary="summary")
    created_requirement = requirements.create_requirement(project, requirement_input)

    # Mock _set_jira_project
    requirements._set_jira_project = Mock()

    # Test listing
    requirements.list_requirements(query_jira=True)
    requirements._set_jira_project.assert_called_once_with(created_requirement)


def test_count_requirements(requirements: Requirements, project: Project):
    # Create some test data
    requirement_inputs = [
        RequirementInput(reference="apple", summary="apple_summary"),
        RequirementInput(reference="banana", summary="banana_summary"),
        RequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for requirement_input in requirement_inputs:
        requirements.create_requirement(project, requirement_input)

    # Test counting requirements without any filters
    results = requirements.count_requirements()
    assert results == len(requirement_inputs)


def test_list_requirement_values(requirements: Requirements, project: Project):
    # Create some test data
    requirement_inputs = [
        RequirementInput(reference="apple", summary="apple_summary"),
        RequirementInput(reference="apple", summary="banana_summary"),
        RequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for requirement_input in requirement_inputs:
        requirements.create_requirement(project, requirement_input)

    # Test listing requirement values without any filters
    results = requirements.list_requirement_values(Requirement.reference)
    assert len(results) == 2
    assert set(results) == {"apple", "cherry"}


def test_list_requirement_values_where_clause(
    requirements: Requirements, project: Project
):
    # Create some test data
    requirement_inputs = [
        RequirementInput(reference="apple", summary="apple_summary"),
        RequirementInput(reference="apple", summary="banana_summary"),
        RequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for requirement_input in requirement_inputs:
        requirements.create_requirement(project, requirement_input)

    # Test listing requirement values with a where clause
    where_clauses = [Requirement.reference == "apple"]
    results = requirements.list_requirement_values(
        Requirement.reference, where_clauses=where_clauses
    )
    assert len(results) == 1
    assert results[0] == "apple"


def test_count_requirement_values(requirements: Requirements, project: Project):
    # Create some test data
    requirement_inputs = [
        RequirementInput(reference="apple", summary="apple_summary"),
        RequirementInput(reference="apple", summary="banana_summary"),
        RequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for requirement_input in requirement_inputs:
        requirements.create_requirement(project, requirement_input)

    # Test counting requirement values without any filters
    results = requirements.count_requirement_values(Requirement.reference)
    assert results == 2


def test_count_requirement_values_where_clause(
    requirements: Requirements, project: Project
):
    # Create some test data
    requirement_inputs = [
        RequirementInput(reference="apple", summary="apple_summary"),
        RequirementInput(reference="apple", summary="banana_summary"),
        RequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for requirement_input in requirement_inputs:
        requirements.create_requirement(project, requirement_input)

    # Test counting requirement values with a where clause
    where_clauses = [Requirement.reference == "apple"]
    results = requirements.count_requirement_values(
        Requirement.reference, where_clauses=where_clauses
    )
    assert results == 1


def test_create_requirement_from_requirement_input(
    requirements: Requirements,
    project: Project,
    catalog_requirement: CatalogRequirement,
):
    # Test creating a requirement from a requirement input
    requirement_input = RequirementInput(
        reference="apple",
        summary="apple_summary",
        catalog_requirement_id=catalog_requirement.id,
    )
    requirement = requirements.create_requirement(project, requirement_input)

    # Check if the requirement is created with the correct data
    assert requirement.id is not None
    assert requirement.reference == requirement_input.reference
    assert requirement.summary == requirement_input.summary
    assert (
        requirement.catalog_requirement_id == requirement_input.catalog_requirement_id
    )


def test_create_requirement_from_requirement_input_no_catalog_requirement_id(
    requirements: Requirements, project: Project
):
    # Test creating a requirement from a requirement input
    requirement_input = RequirementInput(reference="apple", summary="apple_summary")
    requirement = requirements.create_requirement(project, requirement_input)

    # Check if the requirement is created with the correct data
    assert requirement.id is not None
    assert requirement.reference == requirement_input.reference
    assert requirement.summary == requirement_input.summary
    assert requirement.catalog_requirement_id is None


def test_create_requirement_from_requirement_input_invalid_catalog_requirement_id(
    requirements: Requirements, project: Project
):
    # Test creating a requirement from a requirement input
    requirement_input = RequirementInput(
        reference="apple",
        summary="apple_summary",
        catalog_requirement_id=-1,
    )
    with pytest.raises(NotFoundError):
        requirements.create_requirement(project, requirement_input)


def test_create_requirement_from_requirement_import(
    requirements: Requirements, project: Project
):
    # Test creating a requirement from a requirement import
    requirement_import = RequirementImport(
        id=-1,  # should be ignored
        reference="apple",
        summary="apple_summary",
        project=ProjectImport(name="banana_name"),  # should be ignored
        catalog_requirement=CatalogRequirementImport(
            summary="cherry_summary"
        ),  # should be ignored
    )
    requirement = requirements.create_requirement(project, requirement_import)

    # Check if the requirement is created with the correct data
    assert requirement.id is not None
    assert requirement.reference == requirement_import.reference
    assert requirement.summary == requirement_import.summary

    # Check if ignored fields are not changed
    assert requirement.id != requirement_import.id
    assert requirement.project_id == project.id
    assert requirement.catalog_requirement_id is None


def test_create_requirement_skip_flush(
    requirements: Requirements,
    project: Project,
    catalog_requirement: CatalogRequirement,
):
    requirement_input = RequirementInput(
        reference="apple",
        summary="apple_summary",
        catalog_requirement_id=catalog_requirement.id,
    )
    requirements._session = Mock(wraps=requirements._session)

    # Test creating a requirement without flushing the session
    requirements.create_requirement(project, requirement_input, skip_flush=True)

    # Check if the session is not flushed
    requirements._session.flush.assert_not_called()


def test_update_requirement_with_requirement_input(
    requirements: Requirements,
    project: Project,
    catalog_requirement: CatalogRequirement,
):
    # Create a requirement
    requirement_input = RequirementInput(
        reference="apple",
        summary="apple_summary",
        catalog_requirement_id=catalog_requirement.id,
    )
    requirement = requirements.create_requirement(project, requirement_input)

    # Test updating a requirement using RequirementInput
    update_input = RequirementInput(
        reference="updated_apple",
        summary="updated_apple_summary",
        catalog_requirement_id=catalog_requirement.id,
    )
    requirements.update_requirement(requirement, update_input)

    # Check if the requirement is updated with the correct data
    assert requirement.reference == update_input.reference
    assert requirement.summary == update_input.summary
    assert requirement.catalog_requirement_id == update_input.catalog_requirement_id


def test_get_requirement(
    requirements: Requirements,
    project: Project,
    catalog_requirement: CatalogRequirement,
):
    # Create some test data
    requirement_input = RequirementInput(
        reference="apple",
        summary="apple_summary",
        catalog_requirement_id=catalog_requirement.id,
    )
    requirement = requirements.create_requirement(project, requirement_input)

    # Test getting a requirement
    result = requirements.get_requirement(requirement.id)

    # Check if the correct requirement is returned
    assert result.id == requirement.id


def test_get_requirement_not_found(requirements: Requirements):
    # Test getting a requirement with an invalid id
    with pytest.raises(NotFoundError):
        requirements.get_requirement(-1)


def test_update_requirement_with_requirement_import(
    requirements: Requirements, project: Project
):
    # Create a requirement
    requirement_input = RequirementInput(reference="apple", summary="apple_summary")
    requirement = requirements.create_requirement(project, requirement_input)

    # Test updating a requirement using RequirementImport
    update_import = RequirementImport(
        id=-1,  # should be ignored
        reference="updated_apple",
        summary="updated_apple_summary",
        project=ProjectImport(name="banana_name"),  # should be ignored
        catalog_requirement=CatalogRequirementImport(
            summary="cherry_summary"
        ),  # should be ignored
    )
    requirements.update_requirement(requirement, update_import)

    # Check if the requirement is updated with the correct data
    assert requirement.reference == update_import.reference
    assert requirement.summary == update_import.summary

    # Check if ignored fields are not changed
    assert requirement.id != update_import.id
    assert requirement.catalog_requirement_id is None


def test_update_requirement_patch_mode(requirements: Requirements, project: Project):
    # Create a requirement
    requirement_input = RequirementInput(reference="apple", summary="apple_summary")
    requirement = requirements.create_requirement(project, requirement_input)

    # Test updating a requirement in patch mode (only specified fields)
    original_reference = requirement.reference
    update_input = RequirementInput(summary="updated_apple_summary")
    requirements.update_requirement(requirement, update_input, patch=True)

    # Check if the specified field is updated and other fields remain unchanged
    assert requirement.reference == original_reference
    assert requirement.summary == update_input.summary


def test_update_requirement_skip_flush(
    requirements: Requirements,
    project: Project,
    catalog_requirement: CatalogRequirement,
):
    # Create a requirement
    requirement_input = RequirementInput(
        reference="apple",
        summary="apple_summary",
        catalog_requirement_id=catalog_requirement.id,
    )
    requirement = requirements.create_requirement(project, requirement_input)

    update_input = RequirementInput(
        reference="updated_apple",
        summary="updated_apple_summary",
        catalog_requirement_id=catalog_requirement.id,
    )
    requirements._session = Mock(wraps=requirements._session)

    # Test updating a requirement without flushing the session
    requirements.update_requirement(requirement, update_input, skip_flush=True)

    # Check if the session is not flushed
    requirements._session.flush.assert_not_called()


def test_delete_requirement(
    requirements: Requirements,
    project: Project,
    catalog_requirement: CatalogRequirement,
):
    # Create some test data
    requirement_input = RequirementInput(
        reference="reference",
        summary="summary",
        catalog_requirement_id=catalog_requirement.id,
    )
    requirement = requirements.create_requirement(project, requirement_input)

    # Test deleting the requirement
    requirements.delete_requirement(requirement)

    # Check if the requirement is deleted
    with pytest.raises(NotFoundError):
        requirements.get_requirement(requirement.id)


def test_delete_requirement_skip_flush(
    requirements: Requirements,
    project: Project,
    catalog_requirement: CatalogRequirement,
):
    # Create some test data
    requirement_input = RequirementInput(
        reference="reference",
        summary="summary",
        catalog_requirement_id=catalog_requirement.id,
    )
    requirement = requirements.create_requirement(project, requirement_input)

    requirements._session = Mock(wraps=requirements._session)

    # Test deleting the requirement with skip_flush=True
    requirements.delete_requirement(requirement, skip_flush=True)

    # Check if the flush method was not called
    requirements._session.flush.assert_not_called()


def test_bulk_create_update_requirements_create(
    requirements: Requirements,
    project: Project,
    catalog_requirement: CatalogRequirement,
):
    # Create some test data
    requirement_imports = [
        RequirementImport(reference="reference1", summary="summary1"),
        RequirementImport(reference="reference2", summary="summary2"),
    ]

    # Test creating requirements and provide a fallback project
    created_requirements = list(
        requirements.bulk_create_update_requirements(
            requirement_imports, fallback_project=project
        )
    )

    # Check if the requirements are created with the correct data
    assert len(created_requirements) == 2
    for requirement_import, created_requirement in zip(
        requirement_imports, created_requirements
    ):
        assert created_requirement.id is not None
        assert created_requirement.reference == requirement_import.reference
        assert created_requirement.summary == requirement_import.summary


def test_bulk_create_update_requirements_create_without_fallback_project(
    requirements: Requirements, catalog_requirement: CatalogRequirement
):
    # Create some test data
    requirement_imports = [RequirementImport(reference="reference", summary="summary")]

    # Test creating requirements without providing a fallback project
    with pytest.raises(ValueHttpError):
        list(requirements.bulk_create_update_requirements(requirement_imports))


def test_bulk_create_update_requirements_create_with_nested_project(
    requirements: Requirements,
):
    # Create some test data
    requirement_import = RequirementImport(
        reference="reference",
        summary="summary",
        project=ProjectImport(name="name"),
    )

    # Test creating requirements with nested projects
    created_requirements = list(
        requirements.bulk_create_update_requirements([requirement_import])
    )

    # Check if the requirements are created with the correct data
    assert len(created_requirements) == 1
    created_requirement = created_requirements[0]
    assert created_requirement.id is not None
    assert created_requirement.reference == requirement_import.reference
    assert created_requirement.summary == requirement_import.summary
    assert created_requirement.project_id is not None
    assert created_requirement.project.name == requirement_import.project.name


def test_bulk_create_update_requirements_create_with_nested_catalog_requirement(
    requirements: Requirements,
    project: Project,
    catalog_module: CatalogModule,
):
    # Create some test data
    requirement_import = RequirementImport(
        reference="reference",
        summary="summary",
        catalog_requirement=CatalogRequirementImport(summary="summary"),
    )

    # Test creating requirements with nested catalog_requirement and provide a fallback catalog_module
    created_requirements = list(
        requirements.bulk_create_update_requirements(
            [requirement_import],
            fallback_project=project,
            fallback_catalog_module=catalog_module,
        )
    )

    # Check if the requirements are created with the correct data
    assert len(created_requirements) == 1
    created_requirement = created_requirements[0]
    assert created_requirement.id is not None
    assert created_requirement.reference == requirement_import.reference
    assert created_requirement.summary == requirement_import.summary
    assert created_requirement.catalog_requirement_id is not None
    assert (
        created_requirement.catalog_requirement.summary
        == requirement_import.catalog_requirement.summary
    )


def test_bulk_create_update_requirements_create_without_fallback_catalog_module(
    requirements: Requirements,
    project: Project,
):
    # Create some test data
    requirement_import = RequirementImport(
        reference="reference",
        summary="summary",
        catalog_requirement=CatalogRequirementImport(summary="summary"),
    )

    # Test creating requirements with nested catalog_requirement and without providing a fallback catalog_module
    with pytest.raises(ValueHttpError):
        list(
            requirements.bulk_create_update_requirements(
                [requirement_import], fallback_project=project
            )
        )


@pytest.mark.parametrize("patch", [True, False])  # To archive branch coverage
def test_bulk_create_update_requirements_update(
    requirements: Requirements, project: Project, patch: bool
):
    # Create requirements to update
    requirement_input1 = RequirementInput(reference="ref1", summary="summary1")
    requirement_input2 = RequirementInput(reference="ref2", summary="summary2")
    created_requirement1 = requirements.create_requirement(project, requirement_input1)
    created_requirement2 = requirements.create_requirement(project, requirement_input2)

    # Create requirement imports
    requirement_imports = [
        RequirementImport(
            id=created_requirement1.id,
            reference="new_ref1",
            summary="new_summary1",
            project=ProjectImport(id=project.id, name=project.name),
        ),
        RequirementImport(
            id=created_requirement2.id, reference="new_ref2", summary="new_summary2"
        ),
    ]

    # Update requirements using requirement imports
    updated_requirements = list(
        requirements.bulk_create_update_requirements(
            requirement_imports, project, patch=patch
        )
    )

    # Check if the requirements are updated with the correct data
    assert len(updated_requirements) == 2
    for import_, updated in zip(requirement_imports, updated_requirements):
        assert updated.id == import_.id
        assert updated.reference == import_.reference
        assert updated.summary == import_.summary
        assert updated.project_id == project.id


def test_bulk_create_update_requirements_not_found_error(
    requirements: Requirements,
):
    # Create some test data
    requirement_imports = [RequirementImport(id=-1, reference="ref", summary="summary")]

    # Test updating requirements that do not exist
    with pytest.raises(NotFoundError):
        list(requirements.bulk_create_update_requirements(requirement_imports))


def test_bulk_create_update_requirements_skip_flush(
    requirements: Requirements, project: Project
):
    requirement_imports = [RequirementImport(reference="ref", summary="summary")]
    requirements._session = Mock(wraps=requirements._session)

    # Test creating requirements with skip_flush=True
    list(
        requirements.bulk_create_update_requirements(
            requirement_imports, project, skip_flush=True
        )
    )

    # Check if the flush method was not called
    requirements._session.flush.assert_not_called()


def test_convert_requirement_imports(
    requirements: Requirements,
    project: Project,
    catalog_requirement: CatalogRequirement,
):
    # Create some test data
    requirement_imports = [
        RequirementImport(reference="reference1", summary="summary1"),
        RequirementImport(reference="reference2", summary="summary2"),
    ]

    # Test converting requirement imports to requirements
    requirements_map = requirements.convert_requirement_imports(
        requirement_imports, project
    )

    # Check if the requirement inputs are created with the correct data
    assert len(requirements_map) == 2
    for requirement_import in requirement_imports:
        requirement = requirements_map[requirement_import.etag]
        assert requirement.reference == requirement_import.reference
        assert requirement.summary == requirement_import.summary


def test_bulk_create_requirements_from_catalog_requirements(
    requirements: Requirements,
    project: Project,
    catalog_requirement: CatalogRequirement,
):
    # Create a list of catalog requirements
    catalog_requirements = [catalog_requirement]

    # Test creating requirements from catalog requirements
    created_requirements = list(
        requirements.bulk_create_requirements_from_catalog_requirements(
            project, catalog_requirements
        )
    )

    # Check if the requirements are created with the correct data
    assert len(created_requirements) == 1
    created_requirement = created_requirements[0]
    assert isinstance(created_requirement, Requirement)
    assert created_requirement.summary == catalog_requirement.summary
    assert created_requirement.project.id == project.id


def test_bulk_create_requirements_from_catalog_requirements_skip_flush(
    requirements: Requirements,
    project: Project,
    catalog_requirement: CatalogRequirement,
):
    # Create a list of catalog requirements
    catalog_requirements = [catalog_requirement]

    # Mock the session.flush method to check if it is called or not
    requirements._session = Mock(wraps=requirements._session)

    # Test creating requirements from catalog requirements with skip_flush=True
    list(
        requirements.bulk_create_requirements_from_catalog_requirements(
            project, catalog_requirements, skip_flush=True
        )
    )

    # Check if the flush method was not called
    requirements._session.flush.assert_not_called()
