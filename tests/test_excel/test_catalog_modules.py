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

import mimetypes
from tempfile import NamedTemporaryFile

from fastapi.responses import FileResponse

from mvtool.models import CatalogModule
from mvtool.views.excel.catalog_modules import (
    CatalogModulesExcelView,
    convert_catalog_module_to_row,
    get_catalog_module_excel_headers,
)


def test_get_catalog_modules_excel_headers():
    headers = get_catalog_module_excel_headers([])

    header_names = [h.name for h in headers]
    assert header_names == [
        "Catalog Module ID",
        "Catalog Module Reference",
        "Catalog Module Title",
        "Catalog Module Description",
    ]


def test_convert_catalog_module_to_row(create_catalog_module):
    row = convert_catalog_module_to_row(create_catalog_module)

    # check if row contains all expected key/value pairs
    expected = {
        "Catalog Module ID": create_catalog_module.id,
        "Catalog Module Reference": create_catalog_module.reference,
        "Catalog Module Title": create_catalog_module.title,
        "Catalog Module Description": create_catalog_module.description,
    }
    assert row != expected
    assert all(item in row.items() for item in expected.items())


def test_convert_non_existing_catalog_module_to_row():
    row = convert_catalog_module_to_row(None)

    # check if row contains all expected key/value pairs
    expected = {
        "Catalog Module ID": None,
        "Catalog Module Reference": None,
        "Catalog Module Title": None,
        "Catalog Module Description": None,
    }
    assert row != expected
    assert all(item in row.items() for item in expected.items())


def test_download_catalog_modules_excel(
    catalog_modules_excel_view: CatalogModulesExcelView,
    excel_temp_file: NamedTemporaryFile,
    create_catalog_module: CatalogModule,
):
    filename = "test.xlsx"
    response = catalog_modules_excel_view.download_catalog_modules_excel(
        [], [], temp_file=excel_temp_file, filename=filename
    )

    assert isinstance(response, FileResponse)
    assert response.filename == filename
    assert response.media_type == mimetypes.types_map.get(".xlsx")
