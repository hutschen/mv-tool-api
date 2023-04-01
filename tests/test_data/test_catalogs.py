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
from sqlmodel import Session, desc, or_, select

from mvtool import database
from mvtool.data.catalogs import Catalogs
from mvtool.models.catalogs import Catalog, CatalogImport, CatalogInput
from mvtool.utils.errors import NotFoundError


@pytest.fixture
def session(config) -> Session:
    database.setup_engine(config.database)
    database.create_all()

    for session in database.get_session():
        yield session

    database.drop_all()
    database.dispose_engine()


@pytest.fixture
def catalogs(session: Session):
    return Catalogs(session, None)


def test_modify_catalogs_query_single_where_clause(
    session: Session, catalogs: Catalogs
):
    # Create some test data
    catalogs.create_catalog(CatalogInput(reference="apple", title="apple_title"))
    catalogs.create_catalog(CatalogInput(reference="banana", title="banana_title"))
    catalogs.create_catalog(CatalogInput(reference="cherry", title="cherry_title"))

    # Test filtering with a single where clause
    where_clauses = [Catalog.reference == "apple"]
    query = catalogs._modify_catalogs_query(select(Catalog), where_clauses)
    results = session.exec(query).all()
    assert len(results) == 1
    assert results[0].reference == "apple"


def test_modify_catalogs_query_order_by(session: Session, catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(title="apple_title"))
    catalogs.create_catalog(CatalogInput(title="banana_title"))
    catalogs.create_catalog(CatalogInput(title="cherry_title"))

    # Test ordering
    query = catalogs._modify_catalogs_query(
        select(Catalog), order_by_clauses=[desc(Catalog.id)]
    )
    results = session.exec(query).all()
    assert results[0].id > results[1].id


def test_modify_catalogs_query_pagination(session: Session, catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(title="apple_title"))
    catalogs.create_catalog(CatalogInput(title="banana_title"))
    catalogs.create_catalog(CatalogInput(title="cherry_title"))

    # Test pagination with offset and limit
    query = catalogs._modify_catalogs_query(select(Catalog), offset=1, limit=1)
    results = session.exec(query).all()
    assert len(results) == 1


def test_list_catalogs_no_filters(catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(title="apple_title"))
    catalogs.create_catalog(CatalogInput(title="banana_title"))
    catalogs.create_catalog(CatalogInput(title="cherry_title"))

    # Test listing catalogs without any filters
    results = catalogs.list_catalogs()
    assert len(results) == 3


def test_list_catalogs_with_filter(catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(reference="apple", title="apple_title"))
    catalogs.create_catalog(CatalogInput(reference="banana", title="banana_title"))
    catalogs.create_catalog(CatalogInput(reference="cherry", title="cherry_title"))

    # Test listing catalogs with a filter
    results = catalogs.list_catalogs(where_clauses=[Catalog.reference == "apple"])
    assert len(results) == 1
    assert results[0].reference == "apple"


def test_count_catalogs_no_filter(catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(title="apple_title"))
    catalogs.create_catalog(CatalogInput(title="banana_title"))
    catalogs.create_catalog(CatalogInput(title="cherry_title"))

    # Test counting catalogs without any filters
    count = catalogs.count_catalogs()
    assert count == 3


def test_count_catalogs_with_filter(catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(reference="apple", title="apple_title"))
    catalogs.create_catalog(CatalogInput(reference="banana", title="banana_title"))
    catalogs.create_catalog(CatalogInput(reference="cherry", title="cherry_title"))

    # Test counting catalogs with a filter
    count = catalogs.count_catalogs(where_clauses=[Catalog.reference == "apple"])
    assert count == 1


def test_list_catalog_values_no_filter(catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(reference="apple", title="apple_title"))
    catalogs.create_catalog(CatalogInput(reference="apple", title="banana_title"))
    catalogs.create_catalog(CatalogInput(reference="cherry", title="cherry_title"))

    # Test listing catalog values without any filters
    results = catalogs.list_catalog_values(Catalog.reference)
    assert len(results) == 2
    assert set(results) == {"apple", "cherry"}


def test_list_catalog_values_with_filter(catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(reference="apple", title="apple_title"))
    catalogs.create_catalog(CatalogInput(reference="banana", title="banana_title"))
    catalogs.create_catalog(CatalogInput(reference="cherry", title="cherry_title"))

    # Test listing catalog values with a filter
    results = catalogs.list_catalog_values(
        Catalog.reference, where_clauses=[Catalog.reference == "apple"]
    )
    assert len(results) == 1
    assert results == ["apple"]


def test_count_catalog_values_no_filter(catalogs: Catalogs):
    # Create some test data
    catalogs.create_catalog(CatalogInput(reference="apple", title="apple_title"))
    catalogs.create_catalog(CatalogInput(reference="apple", title="banana_title"))
    catalogs.create_catalog(CatalogInput(reference="cherry", title="cherry_title"))

    # Test counting catalog values without any filters
    count = catalogs.count_catalog_values(Catalog.reference)
    assert count == 2


def test_create_catalog_from_catalog_input(session: Session, catalogs: Catalogs):
    # Test creating a catalog from a CatalogInput
    catalog_input = CatalogInput(reference="apple", title="apple_title")
    catalog = catalogs.create_catalog(catalog_input)

    # Check if the catalog is created with the correct data
    created_catalog = session.get(Catalog, catalog.id)
    assert created_catalog is not None
    assert created_catalog.reference == catalog_input.reference
    assert created_catalog.title == catalog_input.title


def test_create_catalog_from_catalog_import(session: Session, catalogs: Catalogs):
    # Test creating a catalog with CatalogImport
    catalog_import = CatalogImport(reference="banana", title="banana_title")
    catalog = catalogs.create_catalog(catalog_import)

    # Check if the catalog is created with the correct data
    created_catalog = session.get(Catalog, catalog.id)
    assert created_catalog is not None
    assert created_catalog.reference == catalog_import.reference
    assert created_catalog.title == catalog_import.title


def test_create_catalog_skip_flush(catalogs: Catalogs):
    catalog_input = CatalogInput(reference="cherry", title="cherry_title")
    catalogs._session = Mock(wraps=catalogs._session)

    # Test creating a catalog with skip_flush=True
    catalogs.create_catalog(catalog_input, skip_flush=True)

    # Check if the flush method was not called
    catalogs._session.flush.assert_not_called()


def test_get_catalog(catalogs: Catalogs):
    # Create a catalog using the create_catalog method
    catalog_input = CatalogInput(reference="test_reference", title="test_title")
    created_catalog = catalogs.create_catalog(catalog_input)

    # Retrieve the catalog using the get_catalog method
    retrieved_catalog = catalogs.get_catalog(created_catalog.id)

    assert created_catalog.id == retrieved_catalog.id


def test_update_catalog_from_catalog_input(catalogs: Catalogs):
    # Create a catalog using the create_catalog method
    catalog_input = CatalogInput(reference="old_reference", title="old_title")
    catalog = catalogs.create_catalog(catalog_input)

    # Test updating the catalog with CatalogInput
    new_catalog_input = CatalogInput(reference="new_reference", title="new_title")
    catalogs.update_catalog(catalog, new_catalog_input)

    assert catalog.reference == new_catalog_input.reference
    assert catalog.title == new_catalog_input.title


def test_update_catalog_from_catalog_import(catalogs: Catalogs):
    # Create a catalog
    catalog_input = CatalogInput(reference="old_reference", title="old_title")
    catalog = catalogs.create_catalog(catalog_input)

    # Test updating the catalog with CatalogImport
    new_catalog_import = CatalogImport(reference="new_reference", title="new_title")
    catalogs.update_catalog(catalog, new_catalog_import)

    assert catalog.reference == new_catalog_import.reference
    assert catalog.title == new_catalog_import.title


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
    catalog_input = CatalogInput(reference="test_reference", title="test_title")
    created_catalog = catalogs.create_catalog(catalog_input)

    # Delete the catalog using the delete_catalog method
    catalogs.delete_catalog(created_catalog)

    # Try to retrieve the deleted catalog using the get_catalog method
    with pytest.raises(NotFoundError):
        catalogs.get_catalog(created_catalog.id)


def test_delete_catalog_skip_flush(catalogs: Catalogs):
    # Create a catalog using the create_catalog method
    catalog_input = CatalogInput(reference="test_reference", title="test_title")
    created_catalog = catalogs.create_catalog(catalog_input)

    catalogs._session = Mock(wraps=catalogs._session)

    # Test deleting the catalog with skip_flush=True
    catalogs.delete_catalog(created_catalog, skip_flush=True)

    # Check if the flush method was not called
    catalogs._session.flush.assert_not_called()


def test_bulk_create_update_catalogs_create(catalogs: Catalogs):
    catalog_imports = [
        CatalogImport(title="title1"),
        CatalogImport(title="title2"),
    ]

    created_catalogs = list(catalogs.bulk_create_update_catalogs(catalog_imports))

    assert len(created_catalogs) == 2
    for catalog_import, created_catalog in zip(catalog_imports, created_catalogs):
        assert created_catalog.id is not None
        assert created_catalog.title == catalog_import.title


def test_bulk_create_update_catalogs_update(catalogs: Catalogs):
    # Create catalogs
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
    converted_catalogs = catalogs.convert_catalog_imports(catalog_imports)

    # Check if the catalogs have the correct values
    assert len(converted_catalogs) == 2
    for catalog_import in catalog_imports:
        catalog = converted_catalogs[catalog_import.etag]
        assert catalog.title == catalog_import.title
