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
from fastapi.responses import FileResponse
from tempfile import NamedTemporaryFile
from mvtool.views.excel.catalog_requirements import (
    CatalogRequirementsExcelView,
    convert_catalog_requirement_to_row,
    get_catalog_requirement_excel_headers,
)


def test_get_catalog_requirements_excel_headers():
    headers = get_catalog_requirement_excel_headers([])

    header_names = [h.name for h in headers]
    assert header_names == [
        "Catalog Requirement ID",
        "Catalog Requirement Reference",
        "Catalog Requirement Summary",
        "Catalog Requirement Description",
        "Catalog Requirement GS Absicherung",
        "Catalog Requirement GS Verantwortliche",
    ]


def test_convert_catalog_requirement_to_row(create_catalog_requirement):
    row = convert_catalog_requirement_to_row(create_catalog_requirement)

    # check if row contains all expected key/value pairs
    expected = {
        "Catalog Requirement ID": create_catalog_requirement.id,
        "Catalog Requirement Reference": create_catalog_requirement.reference,
        "Catalog Requirement Summary": create_catalog_requirement.summary,
        "Catalog Requirement Description": create_catalog_requirement.description,
        "Catalog Requirement GS Absicherung": create_catalog_requirement.gs_absicherung,
        "Catalog Requirement GS Verantwortliche": create_catalog_requirement.gs_verantwortliche,
    }
    assert row != expected
    assert all(item in row.items() for item in expected.items())


def test_convert_non_existing_catalog_requirement_to_row():
    row = convert_catalog_requirement_to_row(None)

    # check if row contains all expected key/value pairs
    expected = {
        "Catalog Requirement ID": None,
        "Catalog Requirement Reference": None,
        "Catalog Requirement Summary": None,
        "Catalog Requirement Description": None,
        "Catalog Requirement GS Absicherung": None,
        "Catalog Requirement GS Verantwortliche": None,
    }
    assert row != expected
    assert all(item in row.items() for item in expected.items())


def test_download_catalog_requirements_excel(
    catalog_requirements_excel_view: CatalogRequirementsExcelView,
    excel_temp_file: NamedTemporaryFile,
):
    filename = "text.xlsx"
    response = catalog_requirements_excel_view.download_catalog_requirements_excel(
        [], [], temp_file=excel_temp_file, filename=filename
    )

    assert isinstance(response, FileResponse)
    assert response.filename == filename
    assert response.media_type == mimetypes.types_map.get(".xlsx")
