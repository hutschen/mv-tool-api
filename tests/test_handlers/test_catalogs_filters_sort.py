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

from dataclasses import astuple, dataclass

import pytest
from fastapi import HTTPException

from mvtool.handlers.catalogs import get_catalog_filters, get_catalog_sort


@dataclass
class CatalogFilterParams:
    reference: str = None
    title: str = None
    description: str = None
    references: list = None
    ids: list = None
    has_reference: bool = None
    has_description: bool = None
    search: str = None


@pytest.mark.parametrize(
    "params, expected_length",
    [
        (CatalogFilterParams(), 0),
        (CatalogFilterParams(reference="ref*"), 1),
        (CatalogFilterParams(title="title*"), 1),
        (CatalogFilterParams(description="desc*"), 1),
        (CatalogFilterParams(references=["ref1", "ref2"]), 1),
        (CatalogFilterParams(ids=[1, 2]), 1),
        (CatalogFilterParams(has_reference=True), 1),
        (CatalogFilterParams(has_description=True), 1),
        (CatalogFilterParams(search="search"), 1),
    ],
)
def test_get_catalog_filters(params: CatalogFilterParams, expected_length: int):
    filters = get_catalog_filters(*astuple(params))
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
    ],
)
def test_get_catalog_sort(sort_by, sort_order, expected_length):
    sort_clauses = get_catalog_sort(sort_by, sort_order)
    assert isinstance(sort_clauses, list)
    assert len(sort_clauses) == expected_length


def test_get_catalog_sort_invalid_sort_by():
    with pytest.raises(HTTPException) as exc_info:
        get_catalog_sort("invalid", "asc")
    assert exc_info.value.status_code == 400
    assert "Invalid sort_by parameter" in str(exc_info.value.detail)
