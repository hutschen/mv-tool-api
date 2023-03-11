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

from mvtool.models import Catalog
from mvtool.views.excel.catalogs import (
    CatalogsExcelView,
    convert_catalog_to_row,
    get_catalog_excel_headers,
)


def test_get_catalog_excel_headers():
    headers = get_catalog_excel_headers()

    header_names = [h.name for h in headers]
    assert header_names == [
        "Catalog ID",
        "Catalog Reference",
        "Catalog Title",
        "Catalog Description",
    ]


def test_convert_catalog_to_row(create_catalog: Catalog):
    row = convert_catalog_to_row(create_catalog)

    # check if row contains all expected key/value pairs
    assert row == {
        "Catalog ID": create_catalog.id,
        "Catalog Reference": create_catalog.reference,
        "Catalog Title": create_catalog.title,
        "Catalog Description": create_catalog.description,
    }


def test_convert_non_existing_catalog_to_row():
    row = convert_catalog_to_row(None)

    # check if row contains all expected key/value pairs
    assert row == {
        "Catalog ID": None,
        "Catalog Reference": None,
        "Catalog Title": None,
        "Catalog Description": None,
    }


def test_download_catalogs_excel(
    catalogs_excel_view: CatalogsExcelView,
    excel_temp_file: NamedTemporaryFile,
):
    filename = "test.xlsx"
    response = catalogs_excel_view.download_catalogs_excel(
        [], [], temp_file=excel_temp_file, filename=filename
    )

    assert isinstance(response, FileResponse)
    assert response.filename == filename
    assert response.media_type == mimetypes.types_map.get(".xlsx")
