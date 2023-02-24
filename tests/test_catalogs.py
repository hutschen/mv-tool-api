# coding: utf-8
#
# Copyright (C) 2022 Helmar Hutschenreuter
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
from mvtool.models import Catalog, CatalogInput
from mvtool.views.catalogs import CatalogsView


def test_list_catalog_outputs(catalogs_view: CatalogsView, create_catalog: Catalog):
    results = list(catalogs_view.list_catalogs())
    assert len(results) == 1
    catalog_output = results[0]
    assert isinstance(catalog_output, Catalog)
    assert catalog_output.id == create_catalog.id


def test_create_catalog(catalogs_view: CatalogsView, catalog_input: CatalogInput):
    catalog = catalogs_view.create_catalog(catalog_input)
    assert isinstance(catalog, Catalog)
    assert catalog.title == catalog_input.title


def test_get_catalog(catalogs_view: CatalogsView, create_catalog: Catalog):
    catalog = catalogs_view.get_catalog(create_catalog.id)
    assert isinstance(catalog, Catalog)
    assert catalog.id == create_catalog.id


def test_update_catalog(
    catalogs_view: CatalogsView, create_catalog: Catalog, catalog_input: CatalogInput
):
    catalog_input.title += "updated"
    catalog = catalogs_view.update_catalog(create_catalog.id, catalog_input)
    assert isinstance(catalog, Catalog)
    assert catalog.title == catalog_input.title


def test_update_catalog_output_invalid_catalog_id(
    catalogs_view: CatalogsView, catalog_input: CatalogInput
):
    with pytest.raises(HTTPException) as error_info:
        catalogs_view.update_catalog(1, catalog_input)
    assert error_info.value.status_code == 404


def test_delete_catalog(catalogs_view: CatalogsView, create_catalog: Catalog):
    catalogs_view.delete_catalog(create_catalog.id)
    with pytest.raises(HTTPException) as error_info:
        catalogs_view.get_catalog(create_catalog.id)
    assert error_info.value.status_code == 404
