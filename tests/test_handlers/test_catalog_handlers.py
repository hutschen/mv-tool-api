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

from mvtool.data.catalogs import Catalogs
from mvtool.handlers.catalogs import (
    create_catalog,
    delete_catalog,
    get_catalog,
    get_catalog_field_names,
    get_catalog_references,
    get_catalog_representations,
    get_catalogs,
    update_catalog,
)
from mvtool.models.catalogs import (
    Catalog,
    CatalogInput,
    CatalogOutput,
    CatalogRepresentation,
)
from mvtool.utils.pagination import Page


def test_get_catalogs_list(catalogs: Catalogs, catalog: Catalog):
    catalogs_list = get_catalogs([], [], {}, catalogs)

    assert isinstance(catalogs_list, list)
    for catalog_ in catalogs_list:
        assert isinstance(catalog_, Catalog)


def test_get_catalogs_with_pagination(catalogs: Catalogs, catalog: Catalog):
    page_params = dict(offset=0, limit=1)
    catalogs_page = get_catalogs([], [], page_params, catalogs)

    assert isinstance(catalogs_page, Page)
    assert catalogs_page.total_count == 1
    for catalog_ in catalogs_page.items:
        assert isinstance(catalog_, CatalogOutput)


def test_create_catalog(catalogs: Catalogs):
    catalog_input = CatalogInput(title="title")
    created_catalog = create_catalog(catalog_input, catalogs)

    assert isinstance(created_catalog, Catalog)
    assert created_catalog.title == catalog_input.title


def test_get_catalog(catalogs: Catalogs, catalog: Catalog):
    catalog_id = catalog.id
    retrieved_catalog = get_catalog(catalog_id, catalogs)

    assert isinstance(retrieved_catalog, Catalog)
    assert retrieved_catalog.id == catalog_id


def test_update_catalog(catalogs: Catalogs, catalog: Catalog):
    catalog_id = catalog.id
    catalog_input = CatalogInput(title="Updated Catalog")
    updated_catalog = update_catalog(catalog_id, catalog_input, catalogs)

    assert isinstance(updated_catalog, Catalog)
    assert updated_catalog.id == catalog_id
    assert updated_catalog.title == catalog_input.title


def test_delete_catalog(catalogs: Catalogs, catalog: Catalog):
    catalog_id = catalog.id
    delete_catalog(catalog_id, catalogs)

    with pytest.raises(HTTPException) as excinfo:
        get_catalog(catalog_id, catalogs)
    assert excinfo.value.status_code == 404
    assert "No Catalog with id" in excinfo.value.detail


def test_get_catalog_representations_list(catalogs: Catalogs, catalog: Catalog):
    results = get_catalog_representations([], None, [], {}, catalogs)

    assert isinstance(results, list)
    for item in results:
        assert isinstance(item, Catalog)


def test_get_catalog_representations_with_pagination(
    catalogs: Catalogs, catalog: Catalog
):
    page_params = dict(offset=0, limit=1)
    resulting_page = get_catalog_representations([], None, [], page_params, catalogs)

    assert isinstance(resulting_page, Page)
    assert resulting_page.total_count == 1
    for item in resulting_page.items:
        assert isinstance(item, CatalogRepresentation)


def test_get_catalog_representations_local_search(catalogs: Catalogs):
    # Create two catalogs with different titles
    catalog_inputs = [
        CatalogInput(reference="apple", title="apple_title"),
        CatalogInput(reference="banana", title="banana_title"),
    ]
    for catalog_input in catalog_inputs:
        catalogs.create_catalog(catalog_input)

    # Get representations using local_search to filter the catalogs
    local_search = "banana"
    catalog_representations_list = get_catalog_representations(
        [], local_search, [], {}, catalogs
    )

    # Check if the correct catalog is returned after filtering
    assert isinstance(catalog_representations_list, list)
    assert len(catalog_representations_list) == 1
    catalog = catalog_representations_list[0]
    assert isinstance(catalog, Catalog)
    assert catalog.reference == "banana"
    assert catalog.title == "banana_title"


def test_get_catalog_field_names_default_list(catalogs: Catalogs):
    field_names = get_catalog_field_names([], catalogs)

    assert isinstance(field_names, set)
    assert field_names == {"id", "title"}


def test_get_catalog_field_names_full_list(catalogs: Catalogs):
    # Create a catalog to get all fields
    catalog_input = CatalogInput(reference="ref", title="title", description="descr")
    catalogs.create_catalog(catalog_input)

    field_names = get_catalog_field_names([], catalogs)

    # Check if all field names are returned
    assert isinstance(field_names, set)
    assert field_names == {"id", "title", "reference", "description"}


def test_get_catalog_references_list(catalogs: Catalogs):
    # Create a catalog with a reference
    catalog_input = CatalogInput(reference="ref", title="title")
    catalogs.create_catalog(catalog_input)

    # Get references without pagination
    references = get_catalog_references([], None, {}, catalogs)

    # Check if all references are returned
    assert isinstance(references, list)
    assert references == ["ref"]


def test_get_catalog_references_with_pagination(catalogs: Catalogs):
    # Create a catalog with a reference
    catalog_input = CatalogInput(reference="ref", title="title")
    catalogs.create_catalog(catalog_input)

    # Set page_params for pagination
    page_params = dict(offset=0, limit=1)

    # Get references with pagination
    references_page = get_catalog_references([], None, page_params, catalogs)

    # Check if the references are returned as a Page instance with the correct reference
    assert isinstance(references_page, Page)
    assert references_page.total_count == 1
    assert references_page.items == ["ref"]


def test_get_catalog_references_local_search(catalogs: Catalogs):
    # Create two catalogs with different references
    catalog_inputs = [
        CatalogInput(reference="apple", title="title1"),
        CatalogInput(reference="banana", title="title2"),
    ]
    for catalog_input in catalog_inputs:
        catalogs.create_catalog(catalog_input)

    # Get references using local_search to filter the catalogs
    local_search = "apple"
    references = get_catalog_references([], local_search, {}, catalogs)

    # Check if the correct reference is returned after filtering
    assert isinstance(references, list)
    assert references == ["apple"]
