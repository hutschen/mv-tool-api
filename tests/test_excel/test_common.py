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

from mvtool.views.excel.common import ExcelHeader, ExcelView


def test_read_worksheet(filled_worksheet, worksheet_headers, worksheet_rows):
    sut = ExcelView(worksheet_headers)
    sut._convert_from_row = lambda row, *_: row

    results = list(sut._read_worksheet(filled_worksheet))
    assert results == worksheet_rows


def test_read_worksheet_invalid_headers(filled_worksheet):
    sut = ExcelView([ExcelHeader("not_existing")])

    with pytest.raises(HTTPException) as error_info:
        list(sut._read_worksheet(filled_worksheet))

    assert error_info.value.status_code == 400
    assert error_info.value.detail.startswith("Missing headers")


def test_write_worksheet(empty_worksheet, worksheet_headers, worksheet_rows):
    sut = ExcelView(worksheet_headers)
    sut._convert_to_row = lambda row, *_: row

    sut._write_worksheet(empty_worksheet, worksheet_rows)

    # read back the worksheet and compare the rows
    headers = None
    results = []
    for values in empty_worksheet.iter_rows(values_only=True):
        if not headers:
            headers = values
        else:
            results.append(dict(zip(headers, values)))
    assert results == worksheet_rows


def test_write_worksheet_no_rows(empty_worksheet, worksheet_headers):
    sut = ExcelView(worksheet_headers)
    sut._write_worksheet(empty_worksheet, [])

    # read back the worksheet
    headers = None
    row_count = 0
    for values in empty_worksheet.iter_rows(values_only=True):
        if not headers:
            headers = values
        else:
            row_count += 1
    assert headers == tuple(h.name for h in worksheet_headers)
    assert row_count == 0


def test_determine_headers_to_write(empty_worksheet, worksheet_headers):
    # Set worksheet headers optional
    for h in worksheet_headers:
        h.optional = True

    sut = ExcelView(worksheet_headers)
    sut._convert_to_row = lambda row, *_: row

    # Write data to worksheet
    sut._write_worksheet(
        empty_worksheet,
        [
            {"int": 0, "str": "hello", "bool": True, "float": 0.0},
            {"int": 0, "str": "world", "bool": False, "float": 0.0},
            {"int": 0, "str": None, "bool": False, "float": 0.0},
        ],
    )

    # Read headers from worksheet
    for headers in empty_worksheet.iter_rows(values_only=True):
        break
    assert headers == ("str", "bool")
