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

from mvtool.models.common import ETagMixin
from mvtool.tables.columns import (
    Cell,
    Column,
    ColumnGroup,
    MissingColumnsError,
    RowValidationError,
)
from mvtool.tables.dataframe import DataFrame


class NestedModel(ETagMixin):
    field3: str


class MainModel(ETagMixin):
    field1: str
    field2: int
    nested: NestedModel


@pytest.fixture
def column_group():
    nested_column_group = ColumnGroup(
        NestedModel,
        "Nested",
        [
            Column("Field 3", "field3", Column.IMPORT_EXPORT, True),
        ],
        "nested",
    )
    return ColumnGroup(
        MainModel,
        "Group",
        [
            Column("Field 1", "field1", Column.IMPORT_EXPORT, True),
            Column("Field 2", "field2", Column.IMPORT_EXPORT, True),
            nested_column_group,
        ],
        "group",
    )


def test_column_group_is_export(column_group):
    assert column_group.is_export


def test_column_group_is_import(column_group):
    assert column_group.is_import


def test_column_group_export_labels(column_group):
    expected_labels = ["Group Field 1", "Group Field 2", "Nested Field 3"]
    assert list(column_group.export_labels) == expected_labels


def test_column_group_import_labels(column_group):
    expected_labels = ["Group Field 1", "Group Field 2", "Nested Field 3"]
    assert list(column_group.import_labels) == expected_labels


def test_column_group_export_to_row(column_group: ColumnGroup):
    obj = MainModel(field1="A", field2=1, nested=NestedModel(field3="C"))
    exported_row = list(column_group.export_to_row(obj))
    expected_row = [
        Cell("Group Field 1", "A"),
        Cell("Group Field 2", 1),
        Cell("Nested Field 3", "C"),
    ]
    assert exported_row == expected_row


def test_column_group_import_from_row(column_group: ColumnGroup):
    row = [
        Cell("Group Field 1", "A"),
        Cell("Group Field 2", 1),
        Cell("Nested Field 3", "C"),
    ]
    imported_obj: MainModel = column_group.import_from_row(row)
    assert imported_obj.field1 == "A"
    assert imported_obj.field2 == 1
    assert imported_obj.nested.field3 == "C"


def test_column_group_import_from_row_empty_row(column_group: ColumnGroup):
    empty_row = []
    imported_obj = column_group.import_from_row(empty_row)
    assert imported_obj is None


def test_column_group_import_from_row_missing_columns_error(column_group):
    # When cells is empty no error is raised
    cells = [Cell("Group Field 1", "test_string")]
    with pytest.raises(MissingColumnsError):
        column_group.import_from_row(cells)


def test_column_group_import_from_row_validation_error(column_group):
    cells = [
        Cell("Group Field 1", "test_string"),
        Cell("Group Field 2", "not_an_integer"),
    ]
    with pytest.raises(RowValidationError):
        column_group.import_from_row(cells)


def test_column_group_export_to_dataframe(column_group: ColumnGroup):
    objs = [
        MainModel(field1="A", field2=1, nested=NestedModel(field3="C")),
        MainModel(field1="D", field2=3, nested=NestedModel(field3="F")),
    ]

    df = column_group.export_to_dataframe(objs)
    expected_df_data = {
        "Group Field 1": ["A", "D"],
        "Group Field 2": [1, 3],
        "Nested Field 3": ["C", "F"],
    }
    assert df.data == expected_df_data


def test_column_group_import_from_dataframe(column_group: ColumnGroup):
    df = DataFrame()
    df.data = {
        "Group Field 1": ["A", "D"],
        "Group Field 2": [1, 3],
        "Nested Field 3": ["C", "F"],
    }

    imported_objs: list[MainModel] = list(column_group.import_from_dataframe(df))
    assert len(imported_objs) == 2
    assert imported_objs[0].field1 == "A"
    assert imported_objs[0].field2 == 1
    assert imported_objs[0].nested.field3 == "C"
    assert imported_objs[1].field1 == "D"
    assert imported_objs[1].field2 == 3
    assert imported_objs[1].nested.field3 == "F"


def test_import_from_dataframe_skip_emtpy_rows(column_group):
    df = DataFrame()
    df.data = {
        "Group Field 1": ["A", None, "B"],
        "Group Field 2": [1, None, 2],
        "Nested Field 3": ["C", "D", "E"],
    }

    imported_objs = list(column_group.import_from_dataframe(df))

    # Check if the imported objects do not contain None
    assert all(obj is not None for obj in imported_objs)
    assert len(imported_objs) == 2
