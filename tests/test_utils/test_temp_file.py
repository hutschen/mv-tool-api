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

from io import StringIO

import pytest

from mvtool.utils.temp_file import preserved_cursor_position


def test_preserved_cursor_position():
    # Create an in-memory binary stream (it behaves like a file object)
    file_obj = StringIO("Hello World")

    # Move the cursor position
    file_obj.seek(5)
    assert file_obj.tell() == 5

    # Use the context manager and write some data
    with preserved_cursor_position(file_obj):
        file_obj.seek(0)
        file_obj.write("Hello Python")

    # After the context, the cursor's position should be restored
    assert file_obj.tell() == 5

    # Read from the preserved cursor's position to check the written data
    assert file_obj.read() == " Python"


def test_preserved_cursor_position_exception():
    # Create an in-memory binary stream (it behaves like a file object)
    file_obj = StringIO("Hello World")

    # Move the cursor position
    file_obj.seek(5)
    assert file_obj.tell() == 5

    # Use the context manager but raise an exception
    with pytest.raises(RuntimeError) as excinfo:
        with preserved_cursor_position(file_obj):
            file_obj.seek(0)
            file_obj.write("Hello Python")
            raise RuntimeError("Some error")

    # Even after the exception, the cursor's position should be restored
    assert file_obj.tell() == 5
    assert "Some error" in str(excinfo.value)
