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
from sqlmodel import Session, desc, select

from mvtool.data.catalog_modules import CatalogModules
from mvtool.models.catalog_modules import (
    CatalogModule,
    CatalogModuleImport,
    CatalogModuleInput,
)
from mvtool.models.catalogs import Catalog, CatalogImport
from mvtool.utils.errors import NotFoundError, ValueHttpError


def test_modify_catalog_modules_query_where_clause(
    session: Session, catalog_modules: CatalogModules, catalog: Catalog
):
    # Create some test data
    catalog_module_inputs = [
        CatalogModuleInput(reference="apple", title="apple_title"),
        CatalogModuleInput(reference="banana", title="banana_title"),
        CatalogModuleInput(reference="cherry", title="cherry_title"),
    ]
    for catalog_module_input in catalog_module_inputs:
        catalog_modules.create_catalog_module(catalog, catalog_module_input)

    # Test filtering with a single where clause
    where_clauses = [CatalogModule.reference == "banana"]
    query = catalog_modules._modify_catalog_modules_query(
        select(CatalogModule), where_clauses
    )
    results: list[CatalogModule] = session.exec(query).all()
    assert len(results) == 1
    assert results[0].reference == "banana"


def test_modify_catalog_modules_query_order_by(
    session: Session, catalog_modules: CatalogModules, catalog: Catalog
):
    # Create some test data
    catalog_module_inputs = [
        CatalogModuleInput(reference="apple", title="apple_title"),
        CatalogModuleInput(reference="banana", title="banana_title"),
        CatalogModuleInput(reference="cherry", title="cherry_title"),
    ]
    for catalog_module_input in catalog_module_inputs:
        catalog_modules.create_catalog_module(catalog, catalog_module_input)

    # Test ordering
    order_by_clauses = [desc(CatalogModule.reference)]
    query = catalog_modules._modify_catalog_modules_query(
        select(CatalogModule), order_by_clauses=order_by_clauses
    )
    results = session.exec(query).all()
    assert [r.reference for r in results] == ["cherry", "banana", "apple"]


def test_modify_catalog_modules_query_offset(
    session: Session, catalog_modules: CatalogModules, catalog: Catalog
):
    # Create some test data
    catalog_module_inputs = [
        CatalogModuleInput(reference="apple", title="apple_title"),
        CatalogModuleInput(reference="banana", title="banana_title"),
        CatalogModuleInput(reference="cherry", title="cherry_title"),
    ]
    for catalog_module_input in catalog_module_inputs:
        catalog_modules.create_catalog_module(catalog, catalog_module_input)

    # Test offset
    query = catalog_modules._modify_catalog_modules_query(
        select(CatalogModule), offset=2
    )
    results = session.exec(query).all()
    assert len(results) == 1


def test_modify_catalog_modules_query_limit(
    session: Session, catalog_modules: CatalogModules, catalog: Catalog
):
    # Create some test data
    catalog_module_inputs = [
        CatalogModuleInput(reference="apple", title="apple_title"),
        CatalogModuleInput(reference="banana", title="banana_title"),
        CatalogModuleInput(reference="cherry", title="cherry_title"),
    ]
    for catalog_module_input in catalog_module_inputs:
        catalog_modules.create_catalog_module(catalog, catalog_module_input)

    # Test limit
    query = catalog_modules._modify_catalog_modules_query(
        select(CatalogModule), limit=1
    )
    results = session.exec(query).all()
    assert len(results) == 1


def test_list_catalog_modules(catalog_modules: CatalogModules, catalog: Catalog):
    # Create some test data
    catalog_module_inputs = [
        CatalogModuleInput(reference="apple", title="apple_title"),
        CatalogModuleInput(reference="banana", title="banana_title"),
        CatalogModuleInput(reference="cherry", title="cherry_title"),
    ]
    for catalog_module_input in catalog_module_inputs:
        catalog_modules.create_catalog_module(catalog, catalog_module_input)

    # Test listing catalog modules without any filters
    results = catalog_modules.list_catalog_modules()
    assert len(results) == len(catalog_module_inputs)


def test_count_catalog_modules(catalog_modules: CatalogModules, catalog: Catalog):
    # Create some test data
    catalog_module_inputs = [
        CatalogModuleInput(reference="apple", title="apple_title"),
        CatalogModuleInput(reference="banana", title="banana_title"),
        CatalogModuleInput(reference="cherry", title="cherry_title"),
    ]
    for catalog_module_input in catalog_module_inputs:
        catalog_modules.create_catalog_module(catalog, catalog_module_input)

    # Test counting catalog modules without any filters
    results = catalog_modules.count_catalog_modules()
    assert results == len(catalog_module_inputs)


def test_list_catalog_module_values(catalog_modules: CatalogModules, catalog: Catalog):
    # Create some test data
    catalog_module_inputs = [
        CatalogModuleInput(reference="apple", title="apple_title"),
        CatalogModuleInput(reference="apple", title="banana_title"),
        CatalogModuleInput(reference="cherry", title="cherry_title"),
    ]
    for catalog_module_input in catalog_module_inputs:
        catalog_modules.create_catalog_module(catalog, catalog_module_input)

    # Test listing catalog module values without any filters
    results = catalog_modules.list_catalog_module_values(CatalogModule.reference)
    assert len(results) == 2
    assert set(results) == {"apple", "cherry"}


def test_list_catalog_module_values_where_clause(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Create some test data
    catalog_module_inputs = [
        CatalogModuleInput(reference="apple", title="apple_title"),
        CatalogModuleInput(reference="apple", title="banana_title"),
        CatalogModuleInput(reference="cherry", title="cherry_title"),
    ]
    for catalog_module_input in catalog_module_inputs:
        catalog_modules.create_catalog_module(catalog, catalog_module_input)

    # Test listing catalog module values with a where clause
    where_clauses = [CatalogModule.reference == "apple"]
    results = catalog_modules.list_catalog_module_values(
        CatalogModule.reference, where_clauses=where_clauses
    )
    assert len(results) == 1
    assert results[0] == "apple"


def test_count_catalog_module_values(catalog_modules: CatalogModules, catalog: Catalog):
    # Create some test data
    catalog_module_inputs = [
        CatalogModuleInput(reference="apple", title="apple_title"),
        CatalogModuleInput(reference="apple", title="banana_title"),
        CatalogModuleInput(reference="cherry", title="cherry_title"),
    ]
    for catalog_module_input in catalog_module_inputs:
        catalog_modules.create_catalog_module(catalog, catalog_module_input)

    # Test counting catalog module values without any filters
    results = catalog_modules.count_catalog_module_values(CatalogModule.reference)
    assert results == 2


def test_count_catalog_module_values_where_clause(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Create some test data
    catalog_module_inputs = [
        CatalogModuleInput(reference="apple", title="apple_title"),
        CatalogModuleInput(reference="apple", title="banana_title"),
        CatalogModuleInput(reference="cherry", title="cherry_title"),
    ]
    for catalog_module_input in catalog_module_inputs:
        catalog_modules.create_catalog_module(catalog, catalog_module_input)

    # Test counting catalog module values with a where clause
    where_clauses = [CatalogModule.reference == "apple"]
    results = catalog_modules.count_catalog_module_values(
        CatalogModule.reference, where_clauses=where_clauses
    )
    assert results == 1


def test_create_catalog_module_from_catalog_input(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Test creating a catalog module from a catalog input
    catalog_module_input = CatalogModuleInput(reference="apple", title="apple_title")
    catalog_module = catalog_modules.create_catalog_module(
        catalog, catalog_module_input
    )

    # Check if the catalog module is created with the correct data
    assert catalog_module.id is not None
    assert catalog_module.reference == catalog_module_input.reference
    assert catalog_module.title == catalog_module_input.title


def test_create_catalog_module_from_catalog_module_import(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Test creating a catalog module from a catalog module import
    catalog_module_import = CatalogModuleImport(
        id=-1,  # should be ignored
        reference="apple",
        title="apple_title",
        catalog=CatalogImport(title="banana_title"),  # should be ignored
    )
    catalog_module = catalog_modules.create_catalog_module(
        catalog, catalog_module_import
    )

    # Check if the catalog module is created with the correct data
    assert catalog_module.id is not None
    assert catalog_module.reference == catalog_module_import.reference
    assert catalog_module.title == catalog_module_import.title

    # Check if ignored fields are not changed
    assert catalog_module.id != catalog_module_import.id
    assert catalog_module.catalog_id == catalog.id


def test_create_catalog_module_skip_flush(
    catalog_modules: CatalogModules, catalog: Catalog
):
    catalog_module_input = CatalogModuleInput(reference="apple", title="apple_title")
    catalog_modules._session = Mock(wraps=catalog_modules._session)

    # Test creating a catalog module without flushing the session
    catalog_modules.create_catalog_module(
        catalog, catalog_module_input, skip_flush=True
    )

    # Check if the session is not flushed
    catalog_modules._session.flush.assert_not_called()


def test_get_catalog_module(catalog_modules: CatalogModules, catalog: Catalog):
    # Create some test data
    catalog_module_input = CatalogModuleInput(reference="apple", title="apple_title")
    catalog_module = catalog_modules.create_catalog_module(
        catalog, catalog_module_input
    )

    # Test getting a catalog module
    result = catalog_modules.get_catalog_module(catalog_module.id)

    # Check if the correct catalog module is returned
    assert result.id == catalog_module.id


def test_get_catalog_module_not_found(catalog_modules: CatalogModules):
    # Test getting a catalog module that does not exist
    with pytest.raises(NotFoundError):
        catalog_modules.get_catalog_module(-1)


def test_update_catalog_module_from_catalog_module_input(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Create some test data
    catalog_module_input = CatalogModuleInput(reference="old", title="old_title")
    catalog_module = catalog_modules.create_catalog_module(
        catalog, catalog_module_input
    )

    # Test updating a catalog module from a catalog module input
    catalog_module_input = CatalogModuleInput(reference="new", title="new_title")
    catalog_modules.update_catalog_module(catalog_module, catalog_module_input)

    # Check if the catalog module is updated with the correct data
    assert catalog_module.reference == catalog_module_input.reference
    assert catalog_module.title == catalog_module_input.title


def test_update_catalog_module_from_catalog_module_import(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Create some test data
    catalog_module_input = CatalogModuleInput(reference="old", title="old_title")
    catalog_module = catalog_modules.create_catalog_module(
        catalog, catalog_module_input
    )

    # Test updating a catalog module from a catalog module import
    catalog_module_import = CatalogModuleImport(
        id=-1,
        reference="new",
        title="new_title",
        catalog=CatalogImport(title="new_title"),
    )
    catalog_modules.update_catalog_module(catalog_module, catalog_module_import)

    # Check if the catalog module is updated with the correct data
    assert catalog_module.reference == catalog_module_import.reference
    assert catalog_module.title == catalog_module_import.title

    # Check if ignored fields are not changed
    assert catalog_module.id != catalog_module_import.id
    assert catalog_module.catalog_id == catalog.id


def test_update_catalog_module_skip_flush(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Create some test data
    catalog_module_input = CatalogModuleInput(reference="reference", title="title")
    catalog_module = catalog_modules.create_catalog_module(
        catalog, catalog_module_input
    )

    catalog_modules._session = Mock(wraps=catalog_modules._session)

    # Test updating the catalog module with skip_flush=True
    catalog_modules.update_catalog_module(
        catalog_module, catalog_module_input, skip_flush=True
    )

    # Check if the flush method was not called
    catalog_modules._session.flush.assert_not_called()


def test_update_catalog_patch(catalog_modules: CatalogModules, catalog: Catalog):
    # Create some test data
    old_catalog_module_input = CatalogModuleInput(
        reference="old_reference", title="old_title"
    )
    catalog_module = catalog_modules.create_catalog_module(
        catalog, old_catalog_module_input
    )

    # Test updating the catalog module with patch=True
    new_catalog_module_input = CatalogModuleInput(title="new_title")
    catalog_modules.update_catalog_module(
        catalog_module, new_catalog_module_input, patch=True
    )

    # Check if the catalog module is updated with the correct data
    assert catalog_module.reference == old_catalog_module_input.reference
    assert catalog_module.title == new_catalog_module_input.title


def test_delete_catalog_module(catalog_modules: CatalogModules, catalog: Catalog):
    # Create some test data
    catalog_module_input = CatalogModuleInput(reference="reference", title="title")
    catalog_module = catalog_modules.create_catalog_module(
        catalog, catalog_module_input
    )

    # Test deleting the catalog module
    catalog_modules.delete_catalog_module(catalog_module)

    # Check if the catalog module is deleted
    with pytest.raises(NotFoundError):
        catalog_modules.get_catalog_module(catalog_module.id)


def test_delete_catalog_module_skip_flush(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Create some test data
    catalog_module_input = CatalogModuleInput(reference="reference", title="title")
    catalog_module = catalog_modules.create_catalog_module(
        catalog, catalog_module_input
    )

    catalog_modules._session = Mock(wraps=catalog_modules._session)

    # Test deleting the catalog module with skip_flush=True
    catalog_modules.delete_catalog_module(catalog_module, skip_flush=True)

    # Check if the flush method was not called
    catalog_modules._session.flush.assert_not_called()


def test_bulk_create_update_catalog_modules_create(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Create some test data
    catalog_module_imports = [
        CatalogModuleImport(title="title1"),
        CatalogModuleImport(title="title2"),
    ]

    # Test creating catalog modules and provide a fallback catalog
    created_catalog_modules = list(
        catalog_modules.bulk_create_update_catalog_modules(
            catalog_module_imports, catalog
        )
    )

    # Check if the catalog modules are created with the correct data
    assert len(created_catalog_modules) == 2
    for catalog_module_import, created_catalog_module in zip(
        catalog_module_imports, created_catalog_modules
    ):
        assert created_catalog_module.id is not None
        assert created_catalog_module.title == catalog_module_import.title


def test_bulk_create_update_catalog_modules_create_without_fallback_catalog(
    catalog_modules: CatalogModules,
):
    # Create some test data
    catalog_module_imports = [CatalogModuleImport(title="title")]

    # Test creating catalog modules without providing a fallback catalog
    with pytest.raises(ValueHttpError):
        list(catalog_modules.bulk_create_update_catalog_modules(catalog_module_imports))


def test_bulk_create_update_catalog_modules_create_with_nested_catalog(
    catalog_modules: CatalogModules,
):
    # Create some test data
    catalog_module_import = CatalogModuleImport(
        title="title",
        catalog=CatalogImport(title="title"),
    )

    # Test creating catalog modules with nested catalogs
    created_catalog_modules = list(
        catalog_modules.bulk_create_update_catalog_modules([catalog_module_import])
    )

    # Check if the catalog modules are created with the correct data
    assert len(created_catalog_modules) == 1
    created_catalog_module = created_catalog_modules[0]
    assert created_catalog_module.id is not None
    assert created_catalog_module.title == catalog_module_import.title
    assert created_catalog_module.catalog_id is not None
    assert created_catalog_module.catalog.title == catalog_module_import.catalog.title


def test_bulk_create_update_catalog_modules_update(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Create catalog modules to update
    catalog_module_input1 = CatalogModuleInput(title="title1")
    catalog_module_input2 = CatalogModuleInput(title="title2")
    created_catalog_module1 = catalog_modules.create_catalog_module(
        catalog, catalog_module_input1
    )
    created_catalog_module2 = catalog_modules.create_catalog_module(
        catalog, catalog_module_input2
    )

    # Create catalog module imports
    catalog_module_imports = [
        CatalogModuleImport(
            id=created_catalog_module1.id,
            title="new_title1",
            catalog=CatalogImport(id=catalog.id, title=catalog.title),
        ),
        CatalogModuleImport(
            id=created_catalog_module2.id,
            title="new_title2",
        ),
    ]

    # Update catalog modules using catalog module imports
    updated_catalog_modules = list(
        catalog_modules.bulk_create_update_catalog_modules(catalog_module_imports)
    )

    # Check if the catalog modules are updated with the correct data
    assert len(updated_catalog_modules) == 2
    for import_, updated in zip(catalog_module_imports, updated_catalog_modules):
        assert updated.id == import_.id
        assert updated.title == import_.title
        assert updated.catalog_id == catalog.id
        assert updated.catalog.title == catalog.title


def test_bulk_create_update_catalog_modules_not_found_error(
    catalog_modules: CatalogModules,
):
    # Create some test data
    catalog_module_imports = [CatalogModuleImport(id=-1, title="title")]

    # Test updating catalog modules that do not exist
    with pytest.raises(NotFoundError):
        list(catalog_modules.bulk_create_update_catalog_modules(catalog_module_imports))


def test_bulk_create_update_catalog_modules_skip_flush(
    catalog_modules: CatalogModules, catalog: Catalog
):
    catalog_module_imports = [CatalogModuleImport(title="title")]
    catalog_modules._session = Mock(wraps=catalog_modules._session)

    # Test creating catalog modules with skip_flush=True
    list(
        catalog_modules.bulk_create_update_catalog_modules(
            catalog_module_imports, catalog, skip_flush=True
        )
    )

    # Check if the flush method was not called
    catalog_modules._session.flush.assert_not_called()


def test_convert_catalog_module_imports(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Create some test data
    catalog_module_imports = [
        CatalogModuleImport(title="title1"),
        CatalogModuleImport(title="title2"),
    ]

    # Test converting catalog module imports to catalog modules
    catalog_modules_map = catalog_modules.convert_catalog_module_imports(
        catalog_module_imports, catalog
    )

    # Check if the catalog module inputs are created with the correct data
    assert len(catalog_modules_map) == 2
    for catalog_module_import in catalog_module_imports:
        catalog_module = catalog_modules_map[catalog_module_import.etag]
        assert catalog_module.title == catalog_module_import.title
