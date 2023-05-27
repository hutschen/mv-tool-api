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

from dataclasses import asdict, dataclass

import pytest
from fastapi import HTTPException

from mvtool.handlers.catalog_modules import (
    get_catalog_module_filters,
    get_catalog_module_sort,
)


@dataclass
class CatalogModuleFilterParams:
    # filter by pattern
    reference: str | None = None
    title: str | None = None
    description: str | None = None
    neg_reference: bool = False
    neg_title: bool = False
    neg_description: bool = False
    #
    # filter by values
    references: list[str] | None = None
    neg_references: bool = False
    #
    # filter by ids
    ids: list[int] | None = None
    catalog_ids: list[int] | None = None
    neg_ids: bool = False
    neg_catalog_ids: bool = False
    #
    # filter for existence
    has_reference: bool | None = None
    has_description: bool | None = None
    #
    # filter by search string
    search: str | None = None


@pytest.mark.parametrize(
    "params, expected_length",
    [
        # fmt: off
        (CatalogModuleFilterParams(), 0),
        #
        # filter by pattern
        (CatalogModuleFilterParams(reference="ref*"), 1),
        (CatalogModuleFilterParams(title="title*"), 1),
        (CatalogModuleFilterParams(description="desc*"), 1),
        (CatalogModuleFilterParams(reference="ref*", neg_reference=True), 1),
        (CatalogModuleFilterParams(title="title*", neg_title=True), 1),
        (CatalogModuleFilterParams(description="desc*", neg_description=True), 1),
        #
        # filter by values
        (CatalogModuleFilterParams(references=["ref1", "ref2"]), 1),
        (CatalogModuleFilterParams(references=["ref1", "ref2"], neg_references=True), 1),
        #
        # filter by ids
        (CatalogModuleFilterParams(ids=[1, 2]), 1),
        (CatalogModuleFilterParams(catalog_ids=[1, 2]), 1),
        (CatalogModuleFilterParams(ids=[1, 2], neg_ids=True), 1),
        (CatalogModuleFilterParams(catalog_ids=[1, 2], neg_catalog_ids=True), 1),
        #
        # filter for existence
        (CatalogModuleFilterParams(has_reference=True), 1),
        (CatalogModuleFilterParams(has_description=True), 1),
        #
        # filter by search string
        (CatalogModuleFilterParams(search="search"), 1),
        # fmt: on
    ],
)
def test_get_catalog_module_filters(
    params: CatalogModuleFilterParams, expected_length: int
):
    filters = get_catalog_module_filters(**asdict(params))
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
