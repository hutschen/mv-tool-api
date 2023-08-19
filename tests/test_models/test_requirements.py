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
from mvtool.models.requirements import RequirementPatchMany


@pytest.mark.parametrize(
    "requirement_patch_many, expected",
    [
        (
            RequirementPatchMany(summary="Test"),
            {"summary": "Test"},
        ),
        (
            RequirementPatchMany(reference="Ref", summary="Test", description="Desc"),
            {"reference": "Ref", "summary": "Test", "description": "Desc"},
        ),
        (
            # fmt: off
            RequirementPatchMany(reference=AutoNumber(kind="number"), summary="Test"), 
            {"reference": AutoNumber(kind="number").to_value(0), "summary": "Test"},
            # fmt: on
        ),
    ],
)
def test_requirement_patch_many_to_patch(
    requirement_patch_many: RequirementPatchMany, expected: dict
):
    patch = requirement_patch_many.to_patch(0)
    assert patch.model_dump(exclude_unset=True) == expected
