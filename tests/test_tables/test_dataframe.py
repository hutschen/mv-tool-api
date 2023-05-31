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

from mvtool.tables.dataframe import Cell, DataFrame


def test_dataframe_init():
    df = DataFrame(
        [
            [Cell("A", 1), Cell("B", 2)],
            [Cell("A", 3), Cell("B", 4)],
        ]
    )
    assert df.data == {
        "A": [1, 3],
        "B": [2, 4],
    }


def test_dataframe_missing_value():
    df = DataFrame(
        [
            [Cell("A", 1), Cell("B", 2)],
            [Cell("A", 3)],
        ]
    )
    assert df.data == {
        "A": [1, 3],
        "B": [2, None],
    }


def test_dataframe_column_names():
    df = DataFrame(
        [
            [Cell("A", 1), Cell("B", 2)],
            [Cell("A", 3), Cell("B", 4)],
        ]
    )
    assert df.column_names == ["A", "B"]


def test_dataframe_getitem():
    df = DataFrame(
        [
            [Cell("Alpha", 1), Cell("Beta", 2)],
            [Cell("Alpha", 3), Cell("Beta", 4)],
        ]
    )
    sub_df = df["Alpha"]

    assert sub_df.data == {"Alpha": [1, 3]}
    assert sub_df.column_names == ["Alpha"]


def test_dataframe_getitem_multiple_columns():
    df = DataFrame(
        [
            [Cell("A", 1), Cell("B", 2), Cell("C", 3)],
            [Cell("A", 4), Cell("B", 5), Cell("C", 6)],
        ]
    )

    sub_df = df[["A", "B"]]
    assert sub_df.data == {
        "A": [1, 4],
        "B": [2, 5],
    }
    assert sub_df.column_names == ["A", "B"]


def test_dataframe_getitem_invalid_column():
    df = DataFrame([[Cell("A", 1), Cell("B", 2)], [Cell("A", 3), Cell("B", 4)]])

    with pytest.raises(KeyError):
        df["C"]
