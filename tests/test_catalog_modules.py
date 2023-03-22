# coding: utf-8
#
#  Copyright (C) 2022 Helmar Hutschenreuter
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


from fastapi import HTTPException
import pytest
from mvtool.models import (
    Catalog,
    CatalogModule,
    CatalogModuleInput,
    CatalogModuleOutput,
)
from mvtool.views.catalog_modules import CatalogModulesView


def test_list_catalog_module(
    catalog_modules_view: CatalogModulesView,
    create_catalog: Catalog,
    create_catalog_module: CatalogModule,
):
    results = catalog_modules_view.list_catalog_modules(
        [CatalogModule.catalog_id == create_catalog.id]
    )
    assert len(results) == 1
    catalog_module = results[0]
    assert isinstance(catalog_module, CatalogModule)
    assert catalog_module.id == create_catalog_module.id


def test_create_catalog_module(
    catalog_modules_view: CatalogModulesView,
    create_catalog: Catalog,
    catalog_module_input: CatalogModuleInput,
):
    catalog_module = catalog_modules_view.create_catalog_module(
        create_catalog, catalog_module_input
    )
    assert isinstance(catalog_module, CatalogModule)
    assert catalog_module.title == catalog_module_input.title
    assert catalog_module.catalog.id == create_catalog.id


def test_get_catalog_module(
    catalog_modules_view: CatalogModulesView, create_catalog_module: CatalogModule
):
    catalog_module_output = catalog_modules_view.get_catalog_module(
        create_catalog_module.id
    )
    assert isinstance(catalog_module_output, CatalogModule)
    assert catalog_module_output.id == create_catalog_module.id


def test_update_catalog_module(
    catalog_modules_view: CatalogModulesView,
    create_catalog_module: CatalogModule,
    catalog_module_input: CatalogModuleInput,
):
    catalog_module_input.title += "updated"
    catalog_module = catalog_modules_view.update_catalog_module(
        create_catalog_module.id, catalog_module_input
    )
    assert isinstance(catalog_module, CatalogModule)
    assert catalog_module.title == catalog_module_input.title


def test_update_catalog_module_invalid_catalog_module_id(
    catalog_modules_view: CatalogModulesView,
    catalog_module_input: CatalogModuleInput,
):
    with pytest.raises(HTTPException) as error_info:
        catalog_modules_view.update_catalog_module(1, catalog_module_input)
    assert error_info.value.status_code == 404


def test_delete_catalog_module(
    catalog_modules_view: CatalogModulesView,
    create_catalog_module: CatalogModule,
):
    catalog_modules_view.delete_catalog_module(create_catalog_module.id)
    with pytest.raises(HTTPException) as error_info:
        catalog_modules_view.get_catalog_module(create_catalog_module.id)
    assert error_info.value.status_code == 404
