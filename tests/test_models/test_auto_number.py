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

from mvtool.models.common import AutoNumber


@pytest.mark.parametrize(
    "start, step, prefix, suffix, counter, expected",
    [
        (1, 1, "", "", 0, "1"),
        (1, 1, None, None, 0, "1"),
        (2, 2, "pre-", "-suf", 5, "pre-12-suf"),  # with prefix and suffix
        (3, 3, "X", "Y", 2, "X9Y"),  # Other step and start values
        (3, 3, "X", "Y", 3, "X12Y"),
        (3, 3, "X", "Y", 4, "X15Y"),
    ],
)
def test_auto_number_to_value(start, step, prefix, suffix, counter, expected):
    obj = AutoNumber(
        kind="number", start=start, step=step, prefix=prefix, suffix=suffix
    )
    assert obj.to_value(counter) == expected
