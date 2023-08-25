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

import shutil
from tempfile import NamedTemporaryFile, _TemporaryFileWrapper
from typing import Callable

from fastapi import Depends, UploadFile


def get_temp_file(suffix: str | None = None) -> Callable:
    """Creates a callable that returns a context manager which yields a temporary file.

    This should be used together with fastapi's Depends() function.

    Args:
        suffix (str or None, optional): The suffix of the temporary file. Defaults to None.

    Returns:
        callable: Callable that returns a context manager that yields a temporary file.
    """

    def get_temp_file():
        with NamedTemporaryFile(suffix=suffix) as temp_file:
            yield temp_file

    return get_temp_file


def copy_upload_to_temp_file(
    upload_file: UploadFile, temp_file: _TemporaryFileWrapper = Depends(get_temp_file())
) -> _TemporaryFileWrapper:
    """Copies the contents of an upload file to a temporary file.

    Args:
        upload_file (UploadFile): The upload file to copy.
        temp_file (NamedTemporaryFile, optional): The temporary file to copy to.

    Returns:
        NamedTemporaryFile: The temporary file.
    """
    shutil.copyfileobj(upload_file.file, temp_file.file)
    temp_file.file.seek(0)  # Reset cursor after copying
    return temp_file
