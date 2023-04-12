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

import pytest
from fastapi import HTTPException

from mvtool.handlers.catalog_modules import (
    get_catalog_module_filters,
    get_catalog_module_sort,
)


@pytest.mark.parametrize(
    "reference, title, description, references, ids, catalog_ids, has_reference, has_description, search, expected_length",
    [
        (None, None, None, None, None, None, None, None, None, 0),
        ("ref*", None, None, None, None, None, None, None, None, 1),
        (None, "title*", None, None, None, None, None, None, None, 1),
        (None, None, "desc*", None, None, None, None, None, None, 1),
        (None, None, None, ["ref1", "ref2"], None, None, None, None, None, 1),
        (None, None, None, None, [1, 2], None, None, None, None, 1),
        (None, None, None, None, None, [1, 2], None, None, None, 1),
        (None, None, None, None, None, None, True, None, None, 1),
        (None, None, None, None, None, None, None, True, None, 1),
        (None, None, None, None, None, None, None, None, "search", 1),
    ],
)
def test_get_catalog_module_filters(
    reference,
    title,
    description,
    references,
    ids,
    catalog_ids,
    has_reference,
    has_description,
    search,
    expected_length,
):
    filters = get_catalog_module_filters(
        reference,
        title,
        description,
        references,
        ids,
        catalog_ids,
        has_reference,
        has_description,
        search,
    )
    assert isinstance(filters, list)
    assert len(filters) == expected_length


@pytest.mark.parametrize(
    "sort_by, sort_order, expected_length",
    [
        (None, None, 0),
        ("reference", "asc", 2),
        ("reference", "desc", 2),
        ("title", "asc", 2),
        ("title", "desc", 2),
        ("description", "asc", 2),
        ("description", "desc", 2),
        ("catalog", "asc", 3),
        ("catalog", "desc", 3),
    ],
)
def test_get_catalog_module_sort(sort_by, sort_order, expected_length):
    sort_clauses = get_catalog_module_sort(sort_by, sort_order)
    assert isinstance(sort_clauses, list)
    assert len(sort_clauses) == expected_length


def test_get_catalog_module_sort_invalid_sort_by():
    with pytest.raises(HTTPException) as exc_info:
        get_catalog_module_sort("invalid", "asc")
    assert exc_info.value.status_code == 400
    assert "Invalid sort_by parameter" in str(exc_info.value.detail)
