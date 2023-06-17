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

import pytest
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.sql import select

from mvtool.data.catalog_requirements import CatalogRequirements
from mvtool.db.schema import CatalogModule, CatalogRequirement
from mvtool.models.catalog_modules import CatalogModuleImport
from mvtool.models.catalog_requirements import (
    CatalogRequirementImport,
    CatalogRequirementInput,
)
from mvtool.utils.errors import NotFoundError, ValueHttpError


def test_modify_catalog_requirements_query_where_clause(
    session: Session,
    catalog_requirements: CatalogRequirements,
    catalog_module: CatalogModule,
):
    # Create some test data
    catalog_requirement_inputs = [
        CatalogRequirementInput(reference="apple", summary="apple_summary"),
        CatalogRequirementInput(reference="banana", summary="banana_summary"),
        CatalogRequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for catalog_requirement_input in catalog_requirement_inputs:
        catalog_requirements.create_catalog_requirement(
            catalog_module, catalog_requirement_input
        )

    # Test filtering with a single where clause
    where_clauses = [CatalogRequirement.reference == "banana"]
    query = catalog_requirements._modify_catalog_requirements_query(
        select(CatalogRequirement), where_clauses
    )
    results: list[CatalogRequirement] = session.execute(query).scalars().all()

    # Check if the query result is correct
    assert len(results) == 1
    assert results[0].reference == "banana"


def test_modify_catalog_requirements_query_order_by(
    session: Session,
    catalog_requirements: CatalogRequirements,
    catalog_module: CatalogModule,
):
    # Create some test data
    catalog_requirement_inputs = [
        CatalogRequirementInput(reference="apple", summary="apple_summary"),
        CatalogRequirementInput(reference="banana", summary="banana_summary"),
        CatalogRequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for catalog_requirement_input in catalog_requirement_inputs:
        catalog_requirements.create_catalog_requirement(
            catalog_module, catalog_requirement_input
        )

    # Test ordering
    order_by_clauses = [desc(CatalogRequirement.reference)]
    query = catalog_requirements._modify_catalog_requirements_query(
        select(CatalogRequirement), order_by_clauses=order_by_clauses
    )
    results: list[CatalogRequirement] = session.execute(query).scalars().all()

    # Check if the query result is correct
    assert [r.reference for r in results] == ["cherry", "banana", "apple"]


def test_modify_catalog_requirements_query_offset(
    session: Session,
    catalog_requirements: CatalogRequirements,
    catalog_module: CatalogModule,
):
    # Create some test data
    catalog_requirement_inputs = [
        CatalogRequirementInput(reference="apple", summary="apple_summary"),
        CatalogRequirementInput(reference="banana", summary="banana_summary"),
        CatalogRequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for catalog_requirement_input in catalog_requirement_inputs:
        catalog_requirements.create_catalog_requirement(
            catalog_module, catalog_requirement_input
        )

    # Test offset
    query = catalog_requirements._modify_catalog_requirements_query(
        select(CatalogRequirement), offset=2
    )
    results = session.execute(query).scalars().all()
    assert len(results) == 1


def test_modify_catalog_requirements_query_limit(
    session: Session,
    catalog_requirements: CatalogRequirements,
    catalog_module: CatalogModule,
):
    # Create some test data
    catalog_requirement_inputs = [
        CatalogRequirementInput(reference="apple", summary="apple_summary"),
        CatalogRequirementInput(reference="banana", summary="banana_summary"),
        CatalogRequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for catalog_requirement_input in catalog_requirement_inputs:
        catalog_requirements.create_catalog_requirement(
            catalog_module, catalog_requirement_input
        )

    # Test limit
    query = catalog_requirements._modify_catalog_requirements_query(
        select(CatalogRequirement), limit=1
    )
    results = session.execute(query).scalars().all()
    assert len(results) == 1


def test_list_catalog_requirements(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_inputs = [
        CatalogRequirementInput(reference="apple", summary="apple_summary"),
        CatalogRequirementInput(reference="banana", summary="banana_summary"),
        CatalogRequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for catalog_requirement_input in catalog_requirement_inputs:
        catalog_requirements.create_catalog_requirement(
            catalog_module, catalog_requirement_input
        )

    # Test listing catalog requirements without any filters
    results = catalog_requirements.list_catalog_requirements()
    assert len(results) == len(catalog_requirement_inputs)


def test_count_catalog_requirements(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_inputs = [
        CatalogRequirementInput(reference="apple", summary="apple_summary"),
        CatalogRequirementInput(reference="banana", summary="banana_summary"),
        CatalogRequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for catalog_requirement_input in catalog_requirement_inputs:
        catalog_requirements.create_catalog_requirement(
            catalog_module, catalog_requirement_input
        )

    # Test counting catalog requirements without any filters
    results = catalog_requirements.count_catalog_requirements()
    assert results == len(catalog_requirement_inputs)


def test_list_catalog_requirement_values(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_inputs = [
        CatalogRequirementInput(reference="apple", summary="apple_summary"),
        CatalogRequirementInput(reference="apple", summary="banana_summary"),
        CatalogRequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for catalog_requirement_input in catalog_requirement_inputs:
        catalog_requirements.create_catalog_requirement(
            catalog_module, catalog_requirement_input
        )

    # Test listing catalog requirement values without any filters
    results = catalog_requirements.list_catalog_requirement_values(
        CatalogRequirement.reference
    )
    assert len(results) == 2
    assert set(results) == {"apple", "cherry"}


def test_list_catalog_requirement_values_where_clause(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_inputs = [
        CatalogRequirementInput(reference="apple", summary="apple_summary"),
        CatalogRequirementInput(reference="apple", summary="banana_summary"),
        CatalogRequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for catalog_requirement_input in catalog_requirement_inputs:
        catalog_requirements.create_catalog_requirement(
            catalog_module, catalog_requirement_input
        )

    # Test listing catalog requirement values with a where clause
    where_clauses = [CatalogRequirement.reference == "apple"]
    results = catalog_requirements.list_catalog_requirement_values(
        CatalogRequirement.reference, where_clauses=where_clauses
    )
    assert len(results) == 1
    assert results[0] == "apple"


def test_count_catalog_requirement_values(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_inputs = [
        CatalogRequirementInput(reference="apple", summary="apple_summary"),
        CatalogRequirementInput(reference="apple", summary="banana_summary"),
        CatalogRequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for catalog_requirement_input in catalog_requirement_inputs:
        catalog_requirements.create_catalog_requirement(
            catalog_module, catalog_requirement_input
        )

    # Test counting catalog requirement values without any filters
    results = catalog_requirements.count_catalog_requirement_values(
        CatalogRequirement.reference
    )
    assert results == 2


def test_count_catalog_requirement_values_where_clause(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_inputs = [
        CatalogRequirementInput(reference="apple", summary="apple_summary"),
        CatalogRequirementInput(reference="apple", summary="banana_summary"),
        CatalogRequirementInput(reference="cherry", summary="cherry_summary"),
    ]
    for catalog_requirement_input in catalog_requirement_inputs:
        catalog_requirements.create_catalog_requirement(
            catalog_module, catalog_requirement_input
        )

    # Test counting catalog requirement values with a where clause
    where_clauses = [CatalogRequirement.reference == "apple"]
    results = catalog_requirements.count_catalog_requirement_values(
        CatalogRequirement.reference, where_clauses=where_clauses
    )
    assert results == 1


def test_create_catalog_requirement_from_catalog_input(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Test creating a catalog requirement from a catalog input
    catalog_requirement_input = CatalogRequirementInput(
        reference="apple", summary="apple_summary"
    )
    catalog_requirement = catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input
    )

    # Check if the catalog requirement is created with the correct data
    assert catalog_requirement.id is not None
    assert catalog_requirement.reference == catalog_requirement_input.reference
    assert catalog_requirement.summary == catalog_requirement_input.summary


def test_create_catalog_requirement_from_catalog_requirement_import(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Test creating a catalog requirement from a catalog requirement import
    catalog_requirement_import = CatalogRequirementImport(
        id=-1,  # should be ignored
        reference="apple",
        summary="apple_summary",
        catalog_module=CatalogModuleImport(title="banana_title"),  # should be ignored
    )
    catalog_requirement = catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_import
    )

    # Check if the catalog requirement is created with the correct data
    assert catalog_requirement.id is not None
    assert catalog_requirement.reference == catalog_requirement_import.reference
    assert catalog_requirement.summary == catalog_requirement_import.summary

    # Check if ignored fields are not changed
    assert catalog_requirement.id != catalog_requirement_import.id
    assert catalog_requirement.catalog_module_id == catalog_module.id


def test_create_catalog_requirement_skip_flush(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    catalog_requirement_input = CatalogRequirementInput(
        reference="apple", summary="apple_summary"
    )
    catalog_requirements._session = Mock(wraps=catalog_requirements._session)

    # Test creating a catalog requirement without flushing the session
    catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input, skip_flush=True
    )

    # Check if the session is not flushed
    catalog_requirements._session.flush.assert_not_called()


def test_get_catalog_requirement(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_input = CatalogRequirementInput(
        reference="apple", summary="apple_summary"
    )
    catalog_requirement = catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input
    )

    # Test getting created catalog requirement
    result = catalog_requirements.get_catalog_requirement(catalog_requirement.id)

    # Check if the correct catalog requirement is returned
    assert result.id == catalog_requirement.id


def test_get_catalog_requirement_not_found(catalog_requirements: CatalogRequirements):
    # Test getting a catalog requirement that does not exist
    with pytest.raises(NotFoundError):
        catalog_requirements.get_catalog_requirement(-1)


def test_check_catalog_requirement_id_exists(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_input = CatalogRequirementInput(
        reference="apple", summary="apple_summary"
    )
    catalog_requirement = catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input
    )

    # Test checking a catalog requirement ID that exists
    result = catalog_requirements.check_catalog_requirement_id(catalog_requirement.id)

    # Check if the correct catalog requirement is returned
    assert result.id == catalog_requirement.id


def test_check_catalog_requirement_id_not_found(
    catalog_requirements: CatalogRequirements,
):
    # Test checking a catalog requirement ID that does not exist
    with pytest.raises(NotFoundError):
        catalog_requirements.check_catalog_requirement_id(-1)


def test_check_catalog_requirement_id_none(catalog_requirements: CatalogRequirements):
    # Test checking passing None as catalog requirement ID
    assert catalog_requirements.check_catalog_requirement_id(None) is None


def test_update_catalog_requirement_from_catalog_requirement_input(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_input = CatalogRequirementInput(
        reference="old", summary="old_summary"
    )
    catalog_requirement = catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input
    )

    # Test updating a catalog requirement from a catalog requirement input
    catalog_requirement_input = CatalogRequirementInput(
        reference="new", summary="new_summary"
    )
    catalog_requirements.update_catalog_requirement(
        catalog_requirement, catalog_requirement_input
    )

    # Check if the catalog requirement is updated with the correct data
    assert catalog_requirement.reference == catalog_requirement_input.reference
    assert catalog_requirement.summary == catalog_requirement_input.summary


def test_update_catalog_requirement_from_catalog_requirement_import(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_input = CatalogRequirementInput(
        reference="old", summary="old_summary"
    )
    catalog_requirement = catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input
    )

    # Test updating a catalog requirement from a catalog requirement import
    catalog_requirement_import = CatalogRequirementImport(
        id=-1,
        reference="new",
        summary="new_summary",
        catalog_module=CatalogModuleImport(title="new_title"),
    )
    catalog_requirements.update_catalog_requirement(
        catalog_requirement, catalog_requirement_import
    )

    # Check if the catalog requirement is updated with the correct data
    assert catalog_requirement.reference == catalog_requirement_import.reference
    assert catalog_requirement.summary == catalog_requirement_import.summary

    # Check if ignored fields are not changed
    assert catalog_requirement.id != catalog_requirement_import.id
    assert catalog_requirement.catalog_module_id == catalog_module.id


def test_update_catalog_requirement_skip_flush(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_input = CatalogRequirementInput(
        reference="reference", summary="summary"
    )
    catalog_requirement = catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input
    )

    catalog_requirements._session = Mock(wraps=catalog_requirements._session)

    # Test updating the catalog requirement with skip_flush=True
    catalog_requirements.update_catalog_requirement(
        catalog_requirement, catalog_requirement_input, skip_flush=True
    )

    # Check if the flush method was not called
    catalog_requirements._session.flush.assert_not_called()


def test_update_catalog_requirement_patch(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    old_catalog_requirement_input = CatalogRequirementInput(
        reference="old_reference", summary="old_summary"
    )
    catalog_requirement = catalog_requirements.create_catalog_requirement(
        catalog_module, old_catalog_requirement_input
    )

    # Test updating the catalog requirement with patch=True
    new_catalog_requirement_input = CatalogRequirementInput(summary="new_summary")
    catalog_requirements.update_catalog_requirement(
        catalog_requirement, new_catalog_requirement_input, patch=True
    )

    # Check if the catalog requirement is updated with the correct data
    assert catalog_requirement.reference == old_catalog_requirement_input.reference
    assert catalog_requirement.summary == new_catalog_requirement_input.summary


def test_delete_catalog_requirement(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_input = CatalogRequirementInput(
        reference="reference", summary="summary"
    )
    catalog_requirement = catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input
    )

    # Test deleting the catalog requirement
    catalog_requirements.delete_catalog_requirement(catalog_requirement)

    # Check if the catalog requirement is deleted
    with pytest.raises(NotFoundError):
        catalog_requirements.get_catalog_requirement(catalog_requirement.id)


def test_delete_catalog_requirement_skip_flush(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_input = CatalogRequirementInput(
        reference="reference", summary="summary"
    )
    catalog_requirement = catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input
    )

    catalog_requirements._session = Mock(wraps=catalog_requirements._session)

    # Test deleting the catalog requirement with skip_flush=True
    catalog_requirements.delete_catalog_requirement(
        catalog_requirement, skip_flush=True
    )

    # Check if the flush method was not called
    catalog_requirements._session.flush.assert_not_called()


def test_bulk_create_update_catalog_requirements_create(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_imports = [
        CatalogRequirementImport(reference="reference1", summary="summary1"),
        CatalogRequirementImport(reference="reference2", summary="summary2"),
    ]

    # Test creating catalog requirements and provide a fallback catalog module
    created_catalog_requirements = list(
        catalog_requirements.bulk_create_update_catalog_requirements(
            catalog_requirement_imports, catalog_module
        )
    )

    # Check if the catalog requirements are created with the correct data
    assert len(created_catalog_requirements) == 2
    for import_, created in zip(
        catalog_requirement_imports, created_catalog_requirements
    ):
        assert created.id is not None
        assert created.reference == import_.reference
        assert created.summary == import_.summary


def test_bulk_create_update_catalog_requirements_create_without_fallback_catalog_module(
    catalog_requirements: CatalogRequirements,
):
    # Create some test data
    catalog_requirement_imports = [CatalogRequirementImport(summary="summary")]

    # Test creating catalog requirements without providing a fallback catalog module
    with pytest.raises(ValueHttpError):
        list(
            catalog_requirements.bulk_create_update_catalog_requirements(
                catalog_requirement_imports
            )
        )


def test_bulk_create_update_catalog_requirements_create_with_nested_catalog_module(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_import = CatalogRequirementImport(
        summary="summary",
        catalog_module=CatalogModuleImport(title="title"),
    )

    # Test creating catalog requirements with nested catalog modules
    created_catalog_requirements = list(
        catalog_requirements.bulk_create_update_catalog_requirements(
            [catalog_requirement_import],
            catalog_module,  # to indirectly provide a fallback catalog
        )
    )

    # Check if the catalog requirements are created with the correct data
    assert len(created_catalog_requirements) == 1
    created = created_catalog_requirements[0]
    assert created.id is not None
    assert created.summary == catalog_requirement_import.summary
    assert created.catalog_module_id is not None

    # Check if the nested catalog module is created with the correct data
    nested = created.catalog_module
    assert nested.title == catalog_requirement_import.catalog_module.title
    assert nested.catalog_id == catalog_module.catalog_id


def test_bulk_create_update_catalog_requirements_update(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create catalog requirements to update
    catalog_requirement_input1 = CatalogRequirementInput(summary="summary1")
    catalog_requirement_input2 = CatalogRequirementInput(summary="summary2")
    created_catalog_requirement1 = catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input1
    )
    created_catalog_requirement2 = catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input2
    )

    # Create catalog requirement imports
    catalog_requirement_imports = [
        CatalogRequirementImport(
            id=created_catalog_requirement1.id,
            summary="new_summary1",
            catalog_module=CatalogModuleImport(id=catalog_module.id, title="title"),
        ),
        CatalogRequirementImport(
            id=created_catalog_requirement2.id,
            summary="new_summary2",
        ),
    ]

    # Update catalog requirements using catalog requirement imports
    updated_catalog_requirements = list(
        catalog_requirements.bulk_create_update_catalog_requirements(
            catalog_requirement_imports
        )
    )

    # Check if the catalog requirements are updated with the correct data
    assert len(updated_catalog_requirements) == 2
    for import_, updated in zip(
        catalog_requirement_imports, updated_catalog_requirements
    ):
        assert updated.id == import_.id
        assert updated.reference == import_.reference
        assert updated.summary == import_.summary
        assert updated.catalog_module_id == catalog_module.id


def test_bulk_create_update_catalog_requirements_not_found_error(
    catalog_requirements: CatalogRequirements,
):
    # Create some test data
    catalog_requirement_imports = [CatalogRequirementImport(id=-1, summary="summary")]

    # Test updating catalog requirements that do not exist
    with pytest.raises(NotFoundError):
        list(
            catalog_requirements.bulk_create_update_catalog_requirements(
                catalog_requirement_imports
            )
        )


def test_bulk_create_update_catalog_requirements_skip_flush(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    catalog_requirement_imports = [CatalogRequirementImport(summary="summary")]
    catalog_requirements._session = Mock(wraps=catalog_requirements._session)

    # Test creating catalog requirements with skip_flush=True
    list(
        catalog_requirements.bulk_create_update_catalog_requirements(
            catalog_requirement_imports, catalog_module, skip_flush=True
        )
    )

    # Check if the flush method was not called
    catalog_requirements._session.flush.assert_not_called()


def test_convert_catalog_requirement_imports(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create some test data
    catalog_requirement_imports = [
        CatalogRequirementImport(summary="summary1"),
        CatalogRequirementImport(summary="summary2"),
    ]

    # Test converting catalog requirement imports to catalog requirements
    catalog_requirements_map = catalog_requirements.convert_catalog_requirement_imports(
        catalog_requirement_imports, catalog_module
    )

    # Check if the catalog requirement inputs are created with the correct data
    assert len(catalog_requirements_map) == 2
    for catalog_requirement_import in catalog_requirement_imports:
        catalog_requirement = catalog_requirements_map[catalog_requirement_import.etag]
        assert catalog_requirement.reference == catalog_requirement_import.reference
        assert catalog_requirement.summary == catalog_requirement_import.summary
