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

from mvtool.tables.columns import Column


@pytest.mark.parametrize(
    "mode, hidden, required, expected_export, expected_import",
    [
        # Test cases for unhidden and required columns
        (Column.IMPORT_EXPORT, False, True, True, True),
        (Column.IMPORT_ONLY, False, True, False, True),
        (Column.EXPORT_ONLY, False, True, True, False),
        #
        # Test cases for hidden and required columns
        (Column.IMPORT_EXPORT, True, True, False, True),
        (Column.IMPORT_ONLY, True, True, False, True),
        (Column.EXPORT_ONLY, True, True, False, False),
        #
        # Test cases for unhidden and non-required columns
        (Column.IMPORT_EXPORT, False, False, True, True),
        (Column.IMPORT_ONLY, False, False, False, True),
        (Column.EXPORT_ONLY, False, False, True, False),
        #
        # Test cases for hidden and non-required columns
        (Column.IMPORT_EXPORT, True, False, False, False),
        (Column.IMPORT_ONLY, True, False, False, False),
        (Column.EXPORT_ONLY, True, False, False, False),
    ],
)
def test_column_is_export_is_import(
    mode, hidden, required, expected_export, expected_import
):
    column = Column("Field 1", "field1", mode, required, hidden)
    assert column.is_export == expected_export
    assert column.is_import == expected_import
