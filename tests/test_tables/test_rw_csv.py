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
import io

import pytest

from mvtool.tables.rw_csv import read_csv
from mvtool.utils.errors import ValueHttpError


@pytest.mark.parametrize(
    "csv_content, dialect_options, expected_data",
    [
        (
            "a,b,c\n1,2,3\n4,5,6\n",
            {},
            {"a": ["1", "4"], "b": ["2", "5"], "c": ["3", "6"]},
        ),
        (
            "a;b;c\n1;2;3\n4;5;6\n",
            {"delimiter": ";"},
            {"a": ["1", "4"], "b": ["2", "5"], "c": ["3", "6"]},
        ),
    ],
)
def test_read_csv_dialect_options(
    csv_content: str,
    dialect_options: dict,
    expected_data: dict,
):
    file_obj = io.BytesIO(csv_content.encode("utf-8"))

    result = read_csv(file_obj, encoding="utf-8", **dialect_options)
    assert result.data == expected_data


@pytest.mark.parametrize(
    "write_encoding, read_encoding",
    [
        ("utf-8", "utf-8"),
        ("utf-8", "utf-8-sig"),  # Write without BOM, read with BOM
        ("utf-8-sig", "utf-8-sig"),  # Write with BOM, read with BOM
    ],
)
def test_read_csv_encoding(write_encoding: str, read_encoding: str):
    csv_content = "a,b,c\n1,2,3\n4,5,6\n"
    file_obj = io.BytesIO(csv_content.encode(write_encoding))

    result = read_csv(file_obj, encoding=read_encoding)
    assert result.data == {"a": ["1", "4"], "b": ["2", "5"], "c": ["3", "6"]}


def test_read_csv_invalid_encoding():
    csv_content = "ä,ö,ü\n1,2,3\n4,5,6\n"
    file_obj = io.BytesIO(csv_content.encode("utf-16"))

    with pytest.raises(ValueHttpError) as e_info:
        read_csv(file_obj, encoding="utf-8")

    assert "Error decoding the CSV file using the 'utf-8' encoding" in str(e_info.value)


def test_read_csv_invalid_columns():
    csv_content = "a,b\n1,2,3\n4,5,6\n"
    file_obj = io.BytesIO(csv_content.encode("utf-8"))

    with pytest.raises(ValueHttpError) as e_info:
        read_csv(file_obj)

    assert "Error reading CSV due to" in str(e_info.value)
