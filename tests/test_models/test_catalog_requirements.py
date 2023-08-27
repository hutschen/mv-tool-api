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

from mvtool.models.catalog_requirements import CatalogRequirementPatchMany
from mvtool.models.common import AutoNumber


@pytest.mark.parametrize(
    "catalog_requirement_patch_many, expected",
    [
        (
            CatalogRequirementPatchMany(summary="test"),
            {"summary": "test"},
        ),
        (
            CatalogRequirementPatchMany(summary="test", reference="test"),
            {"summary": "test", "reference": "test"},
        ),
        (
            # fmt: off
            CatalogRequirementPatchMany(reference=AutoNumber(kind="number"), summary="test"),
            {"reference": AutoNumber(kind="number").to_value(0), "summary": "test"},
            # fmt: on
        ),
    ],
)
def test_catalog_requirement_patch_many_to_patch(
    catalog_requirement_patch_many: CatalogRequirementPatchMany, expected: dict
):
    patch = catalog_requirement_patch_many.to_patch(0)
    assert patch.model_dump(exclude_unset=True) == expected
