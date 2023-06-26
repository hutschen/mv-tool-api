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
from fastapi import HTTPException
from sqlalchemy.orm import Session

from mvtool.data.catalog_modules import CatalogModules
from mvtool.data.catalog_requirements import CatalogRequirements
from mvtool.db.schema import Catalog, CatalogModule, CatalogRequirement
from mvtool.handlers.catalog_requirements import (
    create_catalog_requirement,
    delete_catalog_requirement,
    delete_catalog_requirements,
    get_catalog_requirement,
    get_catalog_requirement_field_names,
    get_catalog_requirement_references,
    get_catalog_requirement_representations,
    get_catalog_requirements,
    patch_catalog_requirement,
    patch_catalog_requirements,
    update_catalog_requirement,
)
from mvtool.models.catalog_requirements import (
    CatalogRequirementInput,
    CatalogRequirementOutput,
    CatalogRequirementPatch,
    CatalogRequirementRepresentation,
)
from mvtool.utils.pagination import Page


def test_get_catalog_requirements_list(catalog_requirements: CatalogRequirements):
    catalog_requirements_list = get_catalog_requirements(
        [], [], {}, catalog_requirements
    )

    assert isinstance(catalog_requirements_list, list)
    for catalog_requirement in catalog_requirements_list:
        assert isinstance(catalog_requirement, CatalogRequirement)


def test_get_catalog_requirements_with_pagination(
    catalog_requirements: CatalogRequirements, catalog_requirement: CatalogRequirement
):
    page_params = dict(offset=0, limit=1)
    catalog_requirements_page = get_catalog_requirements(
        [], [], page_params, catalog_requirements
    )

    assert isinstance(catalog_requirements_page, Page)
    assert catalog_requirements_page.total_count == 1
    for catalog_requirement_ in catalog_requirements_page.items:
        assert isinstance(catalog_requirement_, CatalogRequirementOutput)


def test_create_catalog_requirement(
    catalog_modules: CatalogModules,
    catalog_requirements: CatalogRequirements,
    catalog_module: CatalogModule,
):
    catalog_module_id = catalog_module.id
    catalog_requirement_input = CatalogRequirementInput(
        reference="ref", summary="summary", catalog_module_id=catalog_module_id
    )
    created_catalog_requirement = create_catalog_requirement(
        catalog_module_id,
        catalog_requirement_input,
        catalog_modules,
        catalog_requirements,
    )

    assert isinstance(created_catalog_requirement, CatalogRequirement)
    assert created_catalog_requirement.reference == catalog_requirement_input.reference
    assert created_catalog_requirement.summary == catalog_requirement_input.summary


def test_get_catalog_requirement(
    catalog_requirements: CatalogRequirements, catalog_requirement: CatalogRequirement
):
    catalog_requirement_id = catalog_requirement.id
    retrieved_catalog_requirement = get_catalog_requirement(
        catalog_requirement_id, catalog_requirements
    )

    assert isinstance(retrieved_catalog_requirement, CatalogRequirement)
    assert retrieved_catalog_requirement.id == catalog_requirement_id


def test_update_catalog_requirement(
    catalog_requirements: CatalogRequirements, catalog_requirement: CatalogRequirement
):
    catalog_requirement_id = catalog_requirement.id
    catalog_requirement_input = CatalogRequirementInput(
        reference="Updated ref",
        summary="Updated summary",
        catalog_module_id=catalog_requirement.catalog_module_id,
    )
    updated_catalog_requirement = update_catalog_requirement(
        catalog_requirement_id, catalog_requirement_input, catalog_requirements
    )

    assert isinstance(updated_catalog_requirement, CatalogRequirement)
    assert updated_catalog_requirement.id == catalog_requirement_id
    assert updated_catalog_requirement.reference == catalog_requirement_input.reference
    assert updated_catalog_requirement.summary == catalog_requirement_input.summary


def test_patch_catalog_requirement(
    session: Session, catalog_requirements: CatalogRequirements
):
    # Create catalog requirement
    catalog_requirement = CatalogRequirement(
        reference="reference",
        summary="summary",
        catalog_module=CatalogModule(title="title", catalog=Catalog(title="title")),
    )
    session.add(catalog_requirement)
    session.commit()

    # Patch catalog requirement
    patch = CatalogRequirementPatch(reference="new_reference")
    result = patch_catalog_requirement(
        catalog_requirement.id, patch, catalog_requirements
    )

    # Check if catalog requirement is patched
    assert isinstance(result, CatalogRequirement)
    assert result.reference == "new_reference"
    assert result.summary == "summary"


def test_patch_catalog_requirements(
    session: Session, catalog_requirements: CatalogRequirements
):
    # Create catalog requirements
    catalog_module = CatalogModule(title="title", catalog=Catalog(title="title"))
    for catalog_requirement in [
        # fmt: off
        CatalogRequirement(reference="orange", summary="test", catalog_module=catalog_module),
        CatalogRequirement(reference="peach", summary="test", catalog_module=catalog_module),
        CatalogRequirement(reference="grape", summary="test", catalog_module=catalog_module),
        # fmt: on
    ]:
        session.add(catalog_requirement)
    session.commit()

    # Patch catalog requirements
    patch = CatalogRequirementPatch(reference="grape")
    patch_catalog_requirements(
        patch,
        [CatalogRequirement.reference.in_(["orange", "peach"])],
        catalog_requirements,
    )

    # Check if catalog requirements are patched
    results = session.query(CatalogRequirement).all()
    assert len(results) == 3
    for result in results:
        assert result.reference == "grape"
        assert result.summary == "test"


def test_delete_catalog_requirement(
    catalog_requirements: CatalogRequirements, catalog_requirement: CatalogRequirement
):
    catalog_requirement_id = catalog_requirement.id
    delete_catalog_requirement(catalog_requirement_id, catalog_requirements)

    with pytest.raises(HTTPException) as excinfo:
        get_catalog_requirement(catalog_requirement_id, catalog_requirements)
    assert excinfo.value.status_code == 404
    assert "No CatalogRequirement with id" in excinfo.value.detail


def test_delete_catalog_requirements(
    session: Session, catalog_requirements: CatalogRequirements
):
    # Create catalog requirements
    catalog_module = CatalogModule(
        title="catalog_module", catalog=Catalog(title="catalog")
    )

    for catalog_requirement in [
        CatalogRequirement(summary="apple"),
        CatalogRequirement(summary="banana"),
        CatalogRequirement(summary="cherry"),
    ]:
        session.add(catalog_requirement)
        catalog_requirement.catalog_module = catalog_module
    session.flush()

    # Delete catalog requirements
    delete_catalog_requirements(
        [CatalogRequirement.summary.in_(["apple", "banana"])],
        catalog_requirements,
    )
    session.flush()

    # Check if catalog requirements are deleted
    results = catalog_requirements.list_catalog_requirements()
    assert len(results) == 1
    assert results[0].summary == "cherry"


def test_get_catalog_requirement_representations_list(
    catalog_requirements: CatalogRequirements, catalog_requirement: CatalogRequirement
):
    results = get_catalog_requirement_representations(
        [], None, [], {}, catalog_requirements
    )

    assert isinstance(results, list)
    for item in results:
        assert isinstance(item, CatalogRequirement)


def test_get_catalog_requirement_representations_with_pagination(
    catalog_requirements: CatalogRequirements, catalog_requirement: CatalogRequirement
):
    page_params = dict(offset=0, limit=1)
    resulting_page = get_catalog_requirement_representations(
        [], None, [], page_params, catalog_requirements
    )

    assert isinstance(resulting_page, Page)
    assert resulting_page.total_count == 1
    for item in resulting_page.items:
        assert isinstance(item, CatalogRequirementRepresentation)


def test_get_catalog_requirement_field_names_default_list(catalog_requirements):
    field_names = get_catalog_requirement_field_names([], catalog_requirements)

    assert isinstance(field_names, set)
    assert field_names == {"id", "summary", "catalog_module"}


def test_get_catalog_requirement_field_names_full_list(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create a catalog requirement with all fields
    catalog_requirement_input = CatalogRequirementInput(
        reference="ref",
        summary="summary",
        description="descr",
        gs_absicherung="B",
        gs_verantwortliche="gs_verantwortliche",
        catalog_module_id=catalog_module.id,
    )
    catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input
    )

    field_names = get_catalog_requirement_field_names([], catalog_requirements)

    # Check if all field names are returned
    assert isinstance(field_names, set)
    assert field_names == {
        "id",
        "summary",
        "catalog_module",
        "reference",
        "description",
        "gs_absicherung",
        "gs_verantwortliche",
    }


def test_get_catalog_requirement_representations_list(
    catalog_requirements: CatalogRequirements, catalog_requirement: CatalogRequirement
):
    results = get_catalog_requirement_representations(
        [], None, [], {}, catalog_requirements
    )

    assert isinstance(results, list)
    for item in results:
        assert isinstance(item, CatalogRequirement)


def test_get_catalog_requirement_representations_with_pagination(
    catalog_requirements: CatalogRequirements, catalog_requirement: CatalogRequirement
):
    page_params = dict(offset=0, limit=1)
    resulting_page = get_catalog_requirement_representations(
        [], None, [], page_params, catalog_requirements
    )

    assert isinstance(resulting_page, Page)
    assert resulting_page.total_count == 1
    for item in resulting_page.items:
        assert isinstance(item, CatalogRequirementRepresentation)


def test_get_catalog_requirement_representations_local_search(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create two catalog requirements with different summaries
    catalog_requirement_inputs = [
        CatalogRequirementInput(
            reference="apple",
            summary="apple_summary",
            catalog_module_id=catalog_module.id,
        ),
        CatalogRequirementInput(
            reference="banana",
            summary="banana_summary",
            catalog_module_id=catalog_module.id,
        ),
    ]
    for catalog_requirement_input in catalog_requirement_inputs:
        catalog_requirements.create_catalog_requirement(
            catalog_module, catalog_requirement_input
        )

    # Get representations using local_search to filter the catalog requirements
    local_search = "banana"
    catalog_requirement_representations_list = get_catalog_requirement_representations(
        [], local_search, [], {}, catalog_requirements
    )

    # Check if the correct catalog requirement is returned after filtering
    assert isinstance(catalog_requirement_representations_list, list)
    assert len(catalog_requirement_representations_list) == 1
    catalog_requirement = catalog_requirement_representations_list[0]
    assert isinstance(catalog_requirement, CatalogRequirement)
    assert catalog_requirement.reference == "banana"
    assert catalog_requirement.summary == "banana_summary"


def test_get_catalog_requirement_references_list(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create a catalog requirement with a reference
    catalog_requirement_input = CatalogRequirementInput(
        reference="ref", summary="summary"
    )
    catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input
    )

    # Get references without pagination
    references = get_catalog_requirement_references([], None, {}, catalog_requirements)

    assert isinstance(references, list)
    assert references == ["ref"]


def test_get_catalog_requirement_references_with_pagination(
    catalog_requirements: CatalogRequirements,
    catalog_module: CatalogModule,
):
    # Create another catalog requirement with a different reference
    catalog_requirement_input = CatalogRequirementInput(
        reference="ref", summary="summary"
    )
    catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input
    )

    # Set page_params for pagination
    page_params = dict(offset=0, limit=1)

    # Get references with pagination
    references_page = get_catalog_requirement_references(
        [], None, page_params, catalog_requirements
    )

    # Check if the references are returned as a Page instance with the correct reference
    assert isinstance(references_page, Page)
    assert references_page.total_count == 1
    assert references_page.items == ["ref"]


def test_get_catalog_requirement_references_local_search(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    # Create multiple catalog requirements with different references
    catalog_requirement_inputs = [
        CatalogRequirementInput(reference="apple", summary="apple_summary"),
        CatalogRequirementInput(reference="banana", summary="banana_summary"),
    ]
    for catalog_requirement_input in catalog_requirement_inputs:
        catalog_requirements.create_catalog_requirement(
            catalog_module, catalog_requirement_input
        )

    # Get references using local_search to filter the catalog requirements
    local_search = "banana"
    references = get_catalog_requirement_references(
        [], local_search, {}, catalog_requirements
    )

    assert isinstance(references, list)
    assert references == ["banana"]
