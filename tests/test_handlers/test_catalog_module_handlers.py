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

from io import BytesIO
from tempfile import NamedTemporaryFile
from unittest.mock import Mock

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from mvtool.data.catalog_modules import CatalogModules
from mvtool.data.catalogs import Catalogs
from mvtool.db.schema import Catalog, CatalogModule
from mvtool.gs_parser import GSBausteinParser
from mvtool.handlers.catalog_modules import (
    create_catalog_module,
    delete_catalog_module,
    delete_catalog_modules,
    get_catalog_module,
    get_catalog_module_field_names,
    get_catalog_module_references,
    get_catalog_module_representation,
    get_catalog_modules,
    patch_catalog_module,
    patch_catalog_modules,
    update_catalog_module,
    upload_gs_baustein,
)
from mvtool.models.catalog_modules import (
    CatalogModuleInput,
    CatalogModuleOutput,
    CatalogModulePatch,
    CatalogModulePatchMany,
    CatalogModuleRepresentation,
)
from mvtool.utils.pagination import Page


def test_get_catalog_modules_list(catalog_modules):
    catalog_modules_list = get_catalog_modules([], [], {}, catalog_modules)

    assert isinstance(catalog_modules_list, list)
    for catalog_module in catalog_modules_list:
        assert isinstance(catalog_module, CatalogModule)


def test_get_catalog_modules_with_pagination(catalog_modules, catalog_module):
    page_params = dict(offset=0, limit=1)
    catalog_modules_page = get_catalog_modules([], [], page_params, catalog_modules)

    assert isinstance(catalog_modules_page, Page)
    assert catalog_modules_page.total_count == 1
    for catalog_module_ in catalog_modules_page.items:
        assert isinstance(catalog_module_, CatalogModuleOutput)


def test_create_catalog_module(catalogs, catalog_modules, catalog):
    catalog_id = catalog.id
    catalog_module_input = CatalogModuleInput(title="title", catalog_id=catalog_id)
    created_catalog_module = create_catalog_module(
        catalog_id, catalog_module_input, catalogs, catalog_modules
    )

    assert isinstance(created_catalog_module, CatalogModule)
    assert created_catalog_module.title == catalog_module_input.title
    assert created_catalog_module.catalog_id == catalog_id


def test_get_catalog_module(catalog_modules, catalog_module):
    catalog_module_id = catalog_module.id
    retrieved_catalog_module = get_catalog_module(catalog_module_id, catalog_modules)

    assert isinstance(retrieved_catalog_module, CatalogModule)
    assert retrieved_catalog_module.id == catalog_module_id


def test_update_catalog_module(catalog_modules, catalog_module):
    catalog_module_id = catalog_module.id
    catalog_module_input = CatalogModuleInput(
        title="Updated Catalog Module", catalog_id=catalog_module.catalog_id
    )
    updated_catalog_module = update_catalog_module(
        catalog_module_id, catalog_module_input, catalog_modules
    )

    assert isinstance(updated_catalog_module, CatalogModule)
    assert updated_catalog_module.id == catalog_module_id
    assert updated_catalog_module.title == catalog_module_input.title


def test_patch_catalog_module(session: Session, catalog_modules: CatalogModules):
    # Create catalog module
    catalog_module = CatalogModule(
        reference="reference", title="title", catalog=Catalog(title="catalog")
    )
    session.add(catalog_module)
    session.commit()

    # Patch catalog module
    patch = CatalogModulePatch(reference="new reference")
    result = patch_catalog_module(catalog_module.id, patch, catalog_modules)

    # Check if catalog module is patched
    assert isinstance(result, CatalogModule)
    assert result.reference == "new reference"
    assert result.title == "title"


def test_patch_catalog_modules(session: Session, catalog_modules: CatalogModules):
    # Create catalog modules
    catalog = Catalog(title="catalog")
    for catalog_module in [
        CatalogModule(reference="orange", title="test", catalog=catalog),
        CatalogModule(reference="peach", title="test", catalog=catalog),
        CatalogModule(reference="grape", title="test", catalog=catalog),
    ]:
        session.add(catalog_module)
    session.commit()

    # Patch catalog modules
    patch = CatalogModulePatchMany(reference="grape")
    patch_catalog_modules(
        patch, [CatalogModule.reference.in_(["orange", "peach"])], [], catalog_modules
    )

    # Check if catalog modules are patched
    results = catalog_modules.list_catalog_modules()
    assert len(results) == 3
    for result in results:
        assert isinstance(result, CatalogModule)
        assert result.reference == "grape"
        assert result.title == "test"


def test_delete_catalog_module(catalog_modules, catalog_module):
    catalog_module_id = catalog_module.id
    delete_catalog_module(catalog_module_id, catalog_modules)

    with pytest.raises(HTTPException) as excinfo:
        get_catalog_module(catalog_module_id, catalog_modules)
    assert excinfo.value.status_code == 404
    assert "No CatalogModule with id" in excinfo.value.detail


def test_delete_catalog_modules(session: Session, catalog_modules: CatalogModules):
    # Create catalog modules
    catalog = Catalog(title="catalog")

    for catalog_module in [
        CatalogModule(title="orange"),
        CatalogModule(title="peach"),
        CatalogModule(title="grape"),
    ]:
        session.add(catalog_module)
        catalog_module.catalog = catalog
    session.flush()

    # Delete catalog modules
    delete_catalog_modules(
        [CatalogModule.title.in_(["orange", "peach"])],
        catalog_modules,
    )
    session.flush()

    # Check if catalog modules are deleted
    results = catalog_modules.list_catalog_modules()
    assert len(results) == 1
    assert results[0].title == "grape"


def test_get_catalog_module_representation_list(catalog_modules, catalog_module):
    results = get_catalog_module_representation([], None, [], {}, catalog_modules)

    assert isinstance(results, list)
    for item in results:
        assert isinstance(item, CatalogModule)


def test_get_catalog_module_representation_with_pagination(
    catalog_modules, catalog_module
):
    page_params = dict(offset=0, limit=1)
    resulting_page = get_catalog_module_representation(
        [], None, [], page_params, catalog_modules
    )

    assert isinstance(resulting_page, Page)
    assert resulting_page.total_count == 1
    for item in resulting_page.items:
        assert isinstance(item, CatalogModuleRepresentation)


def test_get_catalog_module_representations_local_search(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Create two catalog modules with different titles
    catalog_module_inputs = [
        CatalogModuleInput(reference="apple", title="apple_title"),
        CatalogModuleInput(reference="banana", title="banana_title"),
    ]
    for catalog_module_input in catalog_module_inputs:
        catalog_modules.create_catalog_module(catalog, catalog_module_input)

    # Get representations using local_search to filter the catalog modules
    local_search = "banana"
    catalog_module_representations_list = get_catalog_module_representation(
        [], local_search, [], {}, catalog_modules
    )

    # Check if the correct catalog module is returned after filtering
    assert isinstance(catalog_module_representations_list, list)
    assert len(catalog_module_representations_list) == 1
    catalog_module = catalog_module_representations_list[0]
    assert isinstance(catalog_module, CatalogModule)
    assert catalog_module.reference == "banana"
    assert catalog_module.title == "banana_title"


def test_get_catalog_module_field_names_default_list(catalog_modules):
    field_names = get_catalog_module_field_names([], catalog_modules)

    assert isinstance(field_names, set)
    assert field_names == {"id", "title", "catalog"}


def test_get_catalog_module_field_names_full_list(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Create a catalog module to get all fields
    catalog_module_input = CatalogModuleInput(
        reference="ref", title="title", description="descr"
    )
    catalog_modules.create_catalog_module(catalog, catalog_module_input)

    field_names = get_catalog_module_field_names([], catalog_modules)

    # Check if all field names are returned
    assert isinstance(field_names, set)
    assert field_names == {"id", "reference", "title", "catalog", "description"}


def test_get_catalog_module_references_list(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Create a catalog module with a reference
    catalog_module_input = CatalogModuleInput(reference="ref", title="title")
    catalog_modules.create_catalog_module(catalog, catalog_module_input)

    # Get references without pagination
    references = get_catalog_module_references([], None, {}, catalog_modules)

    # Check if all references are returned
    assert isinstance(references, list)
    assert references == ["ref"]


def test_get_catalog_module_references_with_pagination(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Create a catalog module with a reference
    catalog_module_input = CatalogModuleInput(reference="ref", title="title")
    catalog_modules.create_catalog_module(catalog, catalog_module_input)

    # Set page_params for pagination
    page_params = dict(offset=0, limit=1)

    # Get references with pagination
    references_page = get_catalog_module_references(
        [], None, page_params, catalog_modules
    )

    # Check if the references are returned as a Page instance with the correct reference
    assert isinstance(references_page, Page)
    assert references_page.total_count == 1
    assert references_page.items == ["ref"]


def test_get_catalog_module_references_local_search(
    catalog_modules: CatalogModules, catalog: Catalog
):
    # Create two catalog modules with different titles
    catalog_module_inputs = [
        CatalogModuleInput(reference="apple", title="apple_title"),
        CatalogModuleInput(reference="banana", title="banana_title"),
    ]
    for catalog_module_input in catalog_module_inputs:
        catalog_modules.create_catalog_module(catalog, catalog_module_input)

    # Get references using local_search to filter the catalog modules
    local_search = "banana"
    references = get_catalog_module_references([], local_search, {}, catalog_modules)

    # Check if the correct reference is returned after filtering
    assert isinstance(references, list)
    assert references == ["banana"]


def test_upload_gs_baustein_success(
    monkeypatch,
    catalog: Catalog,
    catalog_module: CatalogModule,
    session: Session,
    catalogs: Catalogs,
):
    # Prepare mock objects
    parse_mock = Mock()
    parse_mock.return_value = catalog_module
    monkeypatch.setattr(GSBausteinParser, "parse", parse_mock)

    # Create dummy file
    upload_file = UploadFile(BytesIO(b"test"))

    # Create temporary file
    with NamedTemporaryFile(suffix=".docx") as temp_file:
        # Funktion aufrufen
        result = upload_gs_baustein(
            catalog.id,
            upload_file,
            temp_file=temp_file,
            catalogs=catalogs,
            session=session,
        )

    # Check result
    parse_mock.assert_called_once_with(temp_file.name)
    assert result == catalog_module
    assert result.catalog == catalog


def test_upload_gs_baustein_failure(
    monkeypatch,
    catalog: Catalog,
    session: Session,
    catalogs: Catalogs,
):
    # Prepare mock objects
    parse_mock = Mock()
    parse_mock.return_value = None
    monkeypatch.setattr(GSBausteinParser, "parse", parse_mock)

    # Create dummy file
    upload_file = UploadFile(file=BytesIO(b"test"))

    # Create temporary file
    with NamedTemporaryFile(suffix=".docx") as temp_file:
        # Call function and check for ValueHttpError
        with pytest.raises(HTTPException) as exc_info:
            upload_gs_baustein(
                catalog.id,
                upload_file,
                temp_file=temp_file,
                catalogs=catalogs,
                session=session,
            )

    # Check result
    parse_mock.assert_called_once_with(temp_file.name)
    assert exc_info.value.detail == "Could not parse GS Baustein"
