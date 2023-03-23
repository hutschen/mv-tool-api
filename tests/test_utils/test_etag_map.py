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

from mvtool.models.common import ETagMixin
from mvtool.utils.etag_map import get_from_etag_map


class ExampleModel(ETagMixin, BaseModel):
    value: str


# Test cases with different combinations of etag_map and key_obj
@pytest.mark.parametrize(
    "etag_map, key_obj, expected_result, expect_exception",
    [
        # etag_map and key_obj are both None
        (None, None, None, False),
        # etag_map is None, but key_obj is not None
        (None, ExampleModel(value="test_value"), None, True),
        # etag_map is not None, but key_obj is None
        ({}, None, None, False),
    ],
)
def test_get_from_etag_map(etag_map, key_obj, expected_result, expect_exception):
    if expect_exception:
        with pytest.raises(ValueError):
            get_from_etag_map(etag_map, key_obj)
    else:
        assert get_from_etag_map(etag_map, key_obj) == expected_result


# Test case: etag_map and key_obj are both not None, but key_obj is not in etag_map
def test_get_from_etag_map_not_in_map():
    etag_map = {}
    key_obj = ExampleModel(value="test_value")
    with pytest.raises(KeyError):
        get_from_etag_map(etag_map, key_obj)


# Test case: etag_map and key_obj are both not None, and key_obj is in etag_map
def test_get_from_etag_map_in_map():
    key_obj = ExampleModel(value="test_value")
    etag_map = {key_obj.etag: "value"}
    assert get_from_etag_map(etag_map, key_obj) == "value"
