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
from pydantic import BaseModel

from mvtool.utils.models import field_is_set


class MyModel(BaseModel):
    attribute1: str
    attribute2: int = None


def test_field_is_set():
    model = MyModel(attribute1="test")

    # Test if the set field is recognized as set
    assert field_is_set(model, "attribute1") is True

    # Test if the unset field is recognized as not set
    assert field_is_set(model, "attribute2") is False

    # Test if setting an optional field is recognized correctly
    model.attribute2 = 42
    assert field_is_set(model, "attribute2") is True
