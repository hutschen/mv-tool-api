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
import codecs
import io
from unittest.mock import patch

import pytest
from mvtool.tables.dataframe import DataFrame

from mvtool.tables.rw_csv import (
    CSVDialect,
    get_encoding_options,
    lookup_encoding,
    read_csv,
    write_csv,
)
from mvtool.utils.errors import ValueHttpError


def test_lookup_encoding_with_existing_encoding():
    with patch.object(codecs, "lookup") as mock_lookup:
        mock_lookup.return_value = "dummy_value"
        result = lookup_encoding("utf-8")
        assert result == True


def test_lookup_encoding_with_nonexistent_encoding():
    with patch.object(codecs, "lookup") as mock_lookup:
        mock_lookup.side_effect = LookupError
        result = lookup_encoding("non_existent_encoding")
        assert result == False


def test_get_encoding_options():
    # Mock for lookup_encoding that returns True for some encodings and False for others
    def mock_lookup_encoding(encoding):
        return encoding in ["utf-8", "ascii"]

    with patch("mvtool.tables.rw_csv.lookup_encoding", mock_lookup_encoding):
        encoding_options = get_encoding_options()

        # Check if only the encodings where mock_lookup_encoding returns True are included in the result
        assert {"utf-8", "ascii"} == {option.encoding for option in encoding_options}


@pytest.mark.parametrize(
    "csv_content, dialect, expected_data",
    [
        (
            "a,b,c\n1,2,3\n4,5,6\n",
            CSVDialect(),
            {"a": ["1", "4"], "b": ["2", "5"], "c": ["3", "6"]},
        ),
        # Test delimiter option
        (
            "a;b;c\n1;2;3\n4;5;6\n",
            CSVDialect(delimiter=";"),
            {"a": ["1", "4"], "b": ["2", "5"], "c": ["3", "6"]},
        ),
        # Test doublequote option
        (
            'a,"b""b",c\n1,2,3\n4,5,6\n',
            CSVDialect(doublequote=True),
            {"a": ["1", "4"], 'b"b': ["2", "5"], "c": ["3", "6"]},
        ),
        # Test escapechar option
        (
            "a,b\\,b,c\n1,2,3\n4,5,6\n",
            CSVDialect(escapechar="\\"),
            {"a": ["1", "4"], "b,b": ["2", "5"], "c": ["3", "6"]},
        ),
        # Test lineterminator option
        (
            "a,b,c\n1,2,3\n4,5,6\n",
            CSVDialect(lineterminator="lf"),
            {"a": ["1", "4"], "b": ["2", "5"], "c": ["3", "6"]},
        ),
        # Test quotechar option
        (
            "a;'b;b';c\n1;2;3\n4;5;6\n",
            CSVDialect(quotechar="'", delimiter=";"),
            {"a": ["1", "4"], "b;b": ["2", "5"], "c": ["3", "6"]},
        ),
        # Test quoting option (QUOTE_ALL)
        (
            '"a","b","c"\n"1","2","3"\n"4","5","6"\n',
            CSVDialect(quoting="all", quotechar='"'),
            {"a": ["1", "4"], "b": ["2", "5"], "c": ["3", "6"]},
        ),
        # Test quoting option (QUOTE_MINIMAL)
        (
            'a,"b,c",d\n1,"2,3",4\n5,"6,7",8\n',
            CSVDialect(quoting="minimal", quotechar='"'),
            {"a": ["1", "5"], "b,c": ["2,3", "6,7"], "d": ["4", "8"]},
        ),
        # Test quoting option (QUOTE_NONNUMERIC)
        (
            '"a","b","c"\n1.0,2,"3"\n4.0,5,"6"\n',
            CSVDialect(quoting="nonnumeric"),
            {"a": [1.0, 4.0], "b": [2, 5], "c": ["3", "6"]},
        ),
        # Test quoting option (QUOTE_NONE)
        (
            'a,"b",c\n1,"2",3\n4,"5",6\n',
            CSVDialect(quoting="none"),
            {"a": ["1", "4"], '"b"': ['"2"', '"5"'], "c": ["3", "6"]},
        ),
        # Test skipinitialspace option
        (
            "a, b, c\n1, 2, 3\n4, 5, 6\n",
            CSVDialect(skipinitialspace=True),
            {"a": ["1", "4"], "b": ["2", "5"], "c": ["3", "6"]},
        ),
    ],
)
def test_read_csv_dialect_options(
    csv_content: str,
    dialect: dict,
    expected_data: dict,
):
    file_obj = io.BytesIO(csv_content.encode("utf-8"))

    result = read_csv(file_obj, encoding="utf-8", dialect=dialect)
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


def test_read_csv_nonexistent_encoding():
    csv_content = "a,b,c\n1,2,3\n4,5,6\n"
    file_obj = io.BytesIO(csv_content.encode("utf-8"))

    with pytest.raises(ValueHttpError) as e_info:
        read_csv(file_obj, encoding="non_existent_encoding")

    assert "Unsupported encoding: non_existent_encoding" in str(e_info.value)


def test_read_csv_invalid_columns():
    csv_content = "a,b\n1,2,3\n4,5,6\n"
    file_obj = io.BytesIO(csv_content.encode("utf-8"))

    with pytest.raises(ValueHttpError) as e_info:
        read_csv(file_obj)

    assert "Error reading CSV due to" in str(e_info.value)


@pytest.mark.parametrize(
    "data, dialect, expected_csv",
    [
        (
            {"a": [1, 4], "b": [2, 5], "c": [3, 6]},
            CSVDialect(),
            "a,b,c\r\n1,2,3\r\n4,5,6\r\n",
        ),
        # Test delimiter option
        (
            {"a": [1, 4], "b": [2, 5], "c": [3, 6]},
            CSVDialect(delimiter=";"),
            "a;b;c\r\n1;2;3\r\n4;5;6\r\n",
        ),
        # Test doublequote option
        (
            {"a": [1, 4], 'b"b': [2, 5], "c": [3, 6]},
            CSVDialect(doublequote=True),
            'a,"b""b",c\r\n1,2,3\r\n4,5,6\r\n',
        ),
        # Test escapechar option
        (
            {"a": [1, 4], "b,b": [2, 5], "c": [3, 6]},
            CSVDialect(escapechar="\\", quoting="none"),
            "a,b\\,b,c\r\n1,2,3\r\n4,5,6\r\n",
        ),
        # Test lineterminator option
        (
            {"a": [1, 4], "b": [2, 5], "c": [3, 6]},
            CSVDialect(lineterminator="lf"),
            "a,b,c\n1,2,3\n4,5,6\n",
        ),
        # Test quotechar option
        (
            {"a": [1, 4], "b;b": [2, 5], "c": [3, 6]},
            CSVDialect(quotechar="'", delimiter=";"),
            "a;'b;b';c\r\n1;2;3\r\n4;5;6\r\n",
        ),
        # Test quoting option (QUOTE_ALL)
        (
            {"a": [1, 4], "b": [2, 5], "c": [3, 6]},
            CSVDialect(quoting="all", quotechar='"'),
            '"a","b","c"\r\n"1","2","3"\r\n"4","5","6"\r\n',
        ),
        # Test quoting option (QUOTE_MINIMAL)
        (
            {"a": [1, 5], "b,c": ["2,3", "6,7"], "d": [4, 8]},
            CSVDialect(quoting="minimal", quotechar='"'),
            'a,"b,c",d\r\n1,"2,3",4\r\n5,"6,7",8\r\n',
        ),
        # Test quoting option (QUOTE_NONNUMERIC)
        (
            {"a": [1.0, 4.0], "b": [2, 5], "c": ["3", "6"]},
            CSVDialect(quoting="nonnumeric"),
            '"a","b","c"\r\n1.0,2,"3"\r\n4.0,5,"6"\r\n',
        ),
    ],
)
def test_write_csv_dialect_options(data: dict, expected_csv: str, dialect: CSVDialect):
    buffer = io.BytesIO()
    df = DataFrame()
    df.data = data
    write_csv(df, buffer, encoding="utf-8", dialect=dialect)

    assert buffer.getvalue().decode("utf-8") == expected_csv


@pytest.mark.parametrize(
    "write_encoding, read_encoding",
    [
        ("utf-8", "utf-8"),  # Write without BOM, read without BOM
        ("utf-8", "utf-8-sig"),  # Write without BOM, read with BOM
        ("utf-8-sig", "utf-8-sig"),  # Write with BOM, read with BOM
        ("cp1252", "cp1252"),  # Western European (Windows)
        ("iso-8859-1", "iso-8859-1"),  # Western European (ISO) / Latin 1
    ],
)
def test_write_csv_encoding(write_encoding: str, read_encoding: str):
    buffer = io.BytesIO()
    df = DataFrame()
    df.data = {"a": ["1", "4"], "b": ["2", "5"], "c": ["3", "6"]}
    write_csv(df, buffer, encoding=write_encoding)

    expected_csv = ",".join(df.data.keys()) + "\r\n"
    for row in zip(*df.data.values()):
        expected_csv += ",".join(map(str, row)) + "\r\n"

    assert buffer.getvalue().decode(read_encoding) == expected_csv
