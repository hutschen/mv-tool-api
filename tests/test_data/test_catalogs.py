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

from mvtool.data.catalogs import Catalogs
from mvtool.db.schema import Catalog
from mvtool.models.catalogs import CatalogImport, CatalogInput
from mvtool.utils.errors import NotFoundError


def test_modify_catalogs_query_where_clause(session: Session, catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(reference="apple", title="apple_title"))
    catalogs.create_catalog(CatalogInput(reference="banana", title="banana_title"))
    catalogs.create_catalog(CatalogInput(reference="cherry", title="cherry_title"))

    # Test filtering with a single where clause
    where_clauses = [Catalog.reference == "apple"]
    query = catalogs._modify_catalogs_query(select(Catalog), where_clauses)
    results = session.execute(query).scalars().all()
    assert len(results) == 1
    assert results[0].reference == "apple"


def test_modify_catalogs_query_order_by(session: Session, catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(reference="apple", title="apple_title"))
    catalogs.create_catalog(CatalogInput(reference="banana", title="banana_title"))
    catalogs.create_catalog(CatalogInput(reference="cherry", title="cherry_title"))

    # Test ordering
    order_by_clauses = [desc(Catalog.reference)]
    query = catalogs._modify_catalogs_query(
        select(Catalog), order_by_clauses=order_by_clauses
    )
    results = session.execute(query).scalars().all()
    assert [r.reference for r in results] == ["cherry", "banana", "apple"]


def test_modify_catalogs_query_offset(session: Session, catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(title="apple_title"))
    catalogs.create_catalog(CatalogInput(title="banana_title"))
    catalogs.create_catalog(CatalogInput(title="cherry_title"))

    # Test offset
    query = catalogs._modify_catalogs_query(select(Catalog), offset=2)
    results = session.execute(query).scalars().all()
    assert len(results) == 1


def test_modify_catalogs_query_limit(session: Session, catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(title="apple_title"))
    catalogs.create_catalog(CatalogInput(title="banana_title"))
    catalogs.create_catalog(CatalogInput(title="cherry_title"))

    # Test limit
    query = catalogs._modify_catalogs_query(select(Catalog), limit=1)
    results = session.execute(query).scalars().all()
    assert len(results) == 1


def test_list_catalogs(catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(title="apple_title"))
    catalogs.create_catalog(CatalogInput(title="banana_title"))
    catalogs.create_catalog(CatalogInput(title="cherry_title"))

    # Test listing catalogs without any filters
    results = catalogs.list_catalogs()
    assert len(results) == 3


def test_count_catalogs(catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(title="apple_title"))
    catalogs.create_catalog(CatalogInput(title="banana_title"))
    catalogs.create_catalog(CatalogInput(title="cherry_title"))

    # Test counting catalogs without any filters
    count = catalogs.count_catalogs()
    assert count == 3


def test_list_catalog_values(catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(reference="apple", title="apple_title"))
    catalogs.create_catalog(CatalogInput(reference="apple", title="banana_title"))
    catalogs.create_catalog(CatalogInput(reference="cherry", title="cherry_title"))

    # Test listing catalog values without any filters
    results = catalogs.list_catalog_values(Catalog.reference)
    assert len(results) == 2
    assert set(results) == {"apple", "cherry"}


def test_list_catalog_values_where_clause(catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(reference="apple", title="apple_title"))
    catalogs.create_catalog(CatalogInput(reference="banana", title="banana_title"))
    catalogs.create_catalog(CatalogInput(reference="cherry", title="cherry_title"))

    # Test listing catalog values with a where clause
    where_clauses = [Catalog.reference == "apple"]
    results = catalogs.list_catalog_values(
        Catalog.reference, where_clauses=where_clauses
    )
    assert len(results) == 1
    assert results == ["apple"]


def test_count_catalog_values(catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(reference="apple", title="apple_title"))
    catalogs.create_catalog(CatalogInput(reference="apple", title="banana_title"))
    catalogs.create_catalog(CatalogInput(reference="cherry", title="cherry_title"))

    # Test counting catalog values without any filters
    count = catalogs.count_catalog_values(Catalog.reference)
    assert count == 2


def test_count_catalog_values_where_clause(catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(reference="apple", title="apple_title"))
    catalogs.create_catalog(CatalogInput(reference="banana", title="banana_title"))
    catalogs.create_catalog(CatalogInput(reference="cherry", title="cherry_title"))

    # Test counting catalog values with a where clause
    where_clauses = [Catalog.reference == "apple"]
    count = catalogs.count_catalog_values(
        Catalog.reference, where_clauses=where_clauses
    )
    assert count == 1


def test_create_catalog_from_catalog_input(catalogs: Catalogs):
    # Test creating a catalog from a CatalogInput
    catalog_input = CatalogInput(reference="apple", title="apple_title")
    catalog = catalogs.create_catalog(catalog_input)

    # Check if the catalog is created with the correct data
    assert catalog.id is not None
    assert catalog.reference == catalog_input.reference
    assert catalog.title == catalog_input.title


def test_create_catalog_from_catalog_import(catalogs: Catalogs):
    # Test creating a catalog with CatalogImport
    catalog_import = CatalogImport(id=-1, reference="banana", title="banana_title")
    catalog = catalogs.create_catalog(catalog_import)

    # Check if the catalog is created with the correct data
    assert catalog.id is not None
    assert catalog.reference == catalog_import.reference
    assert catalog.title == catalog_import.title

    # Check if ignored fields are not changed
    assert catalog.id != catalog_import.id


def test_create_catalog_skip_flush(catalogs: Catalogs):
    catalog_input = CatalogInput(reference="cherry", title="cherry_title")
    catalogs._session = Mock(wraps=catalogs._session)

    # Test creating a catalog without flushing the session
    catalogs.create_catalog(catalog_input, skip_flush=True)

    # Check if the session is not flushed
    catalogs._session.flush.assert_not_called()


def test_get_catalog(catalogs: Catalogs):
    # Create a catalog using the create_catalog method
    catalog_input = CatalogInput(reference="test_reference", title="test_title")
    created_catalog = catalogs.create_catalog(catalog_input)

    # Retrieve the catalog using the get_catalog method
    result = catalogs.get_catalog(created_catalog.id)

    # Check if the correct catalog is returned
    assert created_catalog.id == result.id


def test_get_catalog_not_found(catalogs: Catalogs):
    # Test getting a catalog that does not exist
    with pytest.raises(NotFoundError):
        catalogs.get_catalog(-1)


def test_update_catalog_from_catalog_input(catalogs: Catalogs):
    # Create a catalog using the create_catalog method
    catalog_input = CatalogInput(reference="old", title="old_title")
    catalog = catalogs.create_catalog(catalog_input)

    # Test updating the catalog with CatalogInput
    new_catalog_input = CatalogInput(reference="new", title="new_title")
    catalogs.update_catalog(catalog, new_catalog_input)

    assert catalog.reference == new_catalog_input.reference
    assert catalog.title == new_catalog_input.title


def test_update_catalog_from_catalog_import(catalogs: Catalogs):
    # Create a catalog
    catalog_input = CatalogInput(reference="old", title="old_title")
    catalog = catalogs.create_catalog(catalog_input)

    # Test updating the catalog with CatalogImport
    new_catalog_import = CatalogImport(id=-1, reference="new", title="new_title")
    catalogs.update_catalog(catalog, new_catalog_import)

    # Check if the catalog is updated with the correct data
    assert catalog.reference == new_catalog_import.reference
    assert catalog.title == new_catalog_import.title

    # Check if ignored fields are not changed
    assert catalog.id != new_catalog_import.id


def test_update_catalog_skip_flush(catalogs: Catalogs):
    # Create a catalog using the create_catalog method
    catalog_input = CatalogInput(reference="reference", title="title")
    catalog = catalogs.create_catalog(catalog_input)

    catalogs._session = Mock(wraps=catalogs._session)

    # Test updating the catalog with skip_flush=True
    catalogs.update_catalog(catalog, catalog_input, skip_flush=True)

    # Check if the flush method was not called
    catalogs._session.flush.assert_not_called()


def test_update_catalog_patch(catalogs: Catalogs):
    # Create a catalog using the create_catalog method
    old_catalog_input = CatalogInput(reference="old_reference", title="old_title")
    catalog = catalogs.create_catalog(old_catalog_input)

    # Test updating the catalog with patch=True
    new_catalog_input = CatalogInput(title="new_title")
    catalogs.update_catalog(catalog, new_catalog_input, patch=True)

    assert catalog.reference == old_catalog_input.reference
    assert catalog.title == new_catalog_input.title


def test_delete_catalog(catalogs: Catalogs):
    # Create a catalog using the create_catalog method
    catalog_input = CatalogInput(reference="reference", title="title")
    created_catalog = catalogs.create_catalog(catalog_input)

    # Delete the catalog using the delete_catalog method
    catalogs.delete_catalog(created_catalog)

    # Check if the catalog is deleted
    with pytest.raises(NotFoundError):
        catalogs.get_catalog(created_catalog.id)


def test_delete_catalog_skip_flush(catalogs: Catalogs):
    # Create a catalog using the create_catalog method
    catalog_input = CatalogInput(reference="reference", title="title")
    created_catalog = catalogs.create_catalog(catalog_input)

    catalogs._session = Mock(wraps=catalogs._session)

    # Test deleting the catalog with skip_flush=True
    catalogs.delete_catalog(created_catalog, skip_flush=True)

    # Check if the flush method was not called
    catalogs._session.flush.assert_not_called()


def test_bulk_create_update_catalogs_create(catalogs: Catalogs):
    # Create some test data
    catalog_imports = [
        CatalogImport(title="title1"),
        CatalogImport(title="title2"),
    ]

    # Test creating catalogs
    created_catalogs = list(catalogs.bulk_create_update_catalogs(catalog_imports))

    # Check if the catalogs are created with the correct data
    assert len(created_catalogs) == 2
    for catalog_import, created_catalog in zip(catalog_imports, created_catalogs):
        assert created_catalog.id is not None
        assert created_catalog.title == catalog_import.title


def test_bulk_create_update_catalogs_update(catalogs: Catalogs):
    # Create catalogs to update
    catalog_input1 = CatalogInput(title="title1")
    catalog_input2 = CatalogInput(title="title2")
    created_catalog1 = catalogs.create_catalog(catalog_input1)
    created_catalog2 = catalogs.create_catalog(catalog_input2)

    # Update catalogs using bulk_create_update_catalogs
    catalog_imports = [
        CatalogImport(id=created_catalog1.id, title="new_title1"),
        CatalogImport(id=created_catalog2.id, title="new_title2"),
    ]

    updated_catalogs = list(catalogs.bulk_create_update_catalogs(catalog_imports))

    assert len(updated_catalogs) == 2
    for catalog_import, updated_catalog in zip(catalog_imports, updated_catalogs):
        assert updated_catalog.id == catalog_import.id
        assert updated_catalog.title == catalog_import.title


def test_bulk_create_update_catalogs_not_found_error(catalogs: Catalogs):
    catalog_imports = [CatalogImport(id=-1, title="title1")]

    with pytest.raises(NotFoundError):
        list(catalogs.bulk_create_update_catalogs(catalog_imports))


def test_bulk_create_update_catalogs_skip_flush(catalogs: Catalogs):
    catalog_imports = [CatalogImport(title="title1")]
    catalogs._session = Mock(wraps=catalogs._session)

    # Test creating catalogs with skip_flush=True
    list(catalogs.bulk_create_update_catalogs(catalog_imports, skip_flush=True))

    # Check if the flush method was not called
    catalogs._session.flush.assert_not_called()


def test_convert_catalog_imports(catalogs: Catalogs):
    catalog_imports = [
        CatalogImport(title="title1"),
        CatalogImport(title="title2"),
    ]

    # Test converting catalog imports to catalogs
    catalog_map = catalogs.convert_catalog_imports(catalog_imports)

    # Check if the catalogs have the correct values
    assert len(catalog_map) == 2
    for catalog_import in catalog_imports:
        catalog = catalog_map[catalog_import.etag]
        assert catalog.title == catalog_import.title
