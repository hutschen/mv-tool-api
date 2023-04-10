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

from typing import Any

import pytest

from mvtool.utils.errors import ValueHttpError
from mvtool.utils.fallback import fallback


# Test scenarios that do not throw errors
@pytest.mark.parametrize(
    "value, default, expected",
    [
        (42, 0, 42),
        (None, 0, 0),
        ("hello", None, "hello"),
        (None, "world", "world"),
        ([1, 2, 3], None, [1, 2, 3]),
        (None, [4, 5, 6], [4, 5, 6]),
    ],
)
def test_fallback(value: Any | None, default: Any | None, expected: Any) -> None:
    result = fallback(value, default)
    assert (
        result == expected
    ), f"Expected fallback to return {expected} for value={value} and default={default}"


def test_fallback_both_none() -> None:
    value: Any = None
    default: Any = None
    error_detail = "Custom error detail"
    with pytest.raises(ValueHttpError, match=error_detail):
        fallback(value, default, error_detail)
