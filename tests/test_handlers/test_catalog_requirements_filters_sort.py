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

from mvtool.handlers.catalog_requirements import (
    get_catalog_requirement_filters,
    get_catalog_requirement_sort,
)


@dataclass
class CatalogRequirementFilterParams:
    reference: str = None
    summary: str = None
    description: str = None
    gs_absicherung: str = None
    gs_verantwortliche: str = None
    references: list = None
    gs_absicherungen: list = None
    ids: list = None
    catalog_ids: list = None
    catalog_module_ids: list = None
    has_reference: bool = None
    has_description: bool = None
    has_gs_absicherung: bool = None
    has_gs_verantwortliche: bool = None
    search: str = None


@pytest.mark.parametrize(
    "params, expected_length",
    [
        (CatalogRequirementFilterParams(), 0),
        (CatalogRequirementFilterParams(reference="ref*"), 1),
        (CatalogRequirementFilterParams(summary="sum*"), 1),
        (CatalogRequirementFilterParams(description="desc*"), 1),
        (CatalogRequirementFilterParams(gs_absicherung="gs_abs*"), 1),
        (CatalogRequirementFilterParams(gs_verantwortliche="gs_ver*"), 1),
        (CatalogRequirementFilterParams(references=["ref1", "ref2"]), 1),
        (CatalogRequirementFilterParams(gs_absicherungen=["gs_abs1", "gs_abs2"]), 1),
        (CatalogRequirementFilterParams(ids=[1, 2]), 1),
        (CatalogRequirementFilterParams(catalog_ids=[1, 2]), 1),
        (CatalogRequirementFilterParams(catalog_module_ids=[1, 2]), 1),
        (CatalogRequirementFilterParams(has_reference=True), 1),
        (CatalogRequirementFilterParams(has_description=True), 1),
        (CatalogRequirementFilterParams(has_gs_absicherung=True), 1),
        (CatalogRequirementFilterParams(has_gs_verantwortliche=True), 1),
        (CatalogRequirementFilterParams(search="search"), 1),
    ],
)
def test_get_catalog_requirement_filters(
    params: CatalogRequirementFilterParams, expected_length: int
):
    filters = get_catalog_requirement_filters(*astuple(params))
    assert len(filters) == expected_length


@pytest.mark.parametrize(
    "sort_by, sort_order, expected_length",
    [
        (None, None, 0),
        ("reference", "asc", 2),
        ("reference", "desc", 2),
        ("summary", "asc", 2),
        ("summary", "desc", 2),
        ("description", "asc", 2),
        ("description", "desc", 2),
        ("gs_absicherung", "asc", 2),
        ("gs_absicherung", "desc", 2),
        ("gs_verantwortliche", "asc", 2),
        ("gs_verantwortliche", "desc", 2),
        ("catalog", "asc", 3),
        ("catalog", "desc", 3),
        ("catalog_module", "asc", 3),
        ("catalog_module", "desc", 3),
    ],
)
def test_get_catalog_requirement_sort(sort_by, sort_order, expected_length):
    sort_clauses = get_catalog_requirement_sort(sort_by, sort_order)
    assert isinstance(sort_clauses, list)
    assert len(sort_clauses) == expected_length


def test_get_catalog_requirement_sort_invalid_sort_by():
    with pytest.raises(HTTPException) as exc_info:
        get_catalog_requirement_sort("invalid", "asc")
    assert exc_info.value.status_code == 400
    assert "Invalid sort_by parameter" in str(exc_info.value.detail)
