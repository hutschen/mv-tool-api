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

from mvtool.handlers.catalog_requirements import (
    get_catalog_requirement_filters,
    get_catalog_requirement_sort,
)


@dataclass
class CatalogRequirementFilterParams:
    # filter by pattern
    reference: str | None = None
    summary: str | None = None
    description: str | None = None
    gs_absicherung: str | None = None
    gs_verantwortliche: str | None = None
    neg_reference: bool = False
    neg_summary: bool = False
    neg_description: bool = False
    neg_gs_absicherung: bool = False
    neg_gs_verantwortliche: bool = False
    #
    # filter by values
    references: list[str] | None = None
    gs_absicherungen: list[str] | None = None
    neg_references: bool = False
    neg_gs_absicherungen: bool = False
    #
    # filter by ids
    ids: list[int] | None = None
    catalog_ids: list[int] | None = None
    catalog_module_ids: list[int] | None = None
    neg_ids: bool = False
    neg_catalog_ids: bool = False
    neg_catalog_module_ids: bool = False
    #
    # filter for existence
    has_reference: bool | None = None
    has_description: bool | None = None
    has_gs_absicherung: bool | None = None
    has_gs_verantwortliche: bool | None = None
    #
    # filter by search string
    search: str | None = None


@pytest.mark.parametrize(
    "params, expected_length",
    [
        # fmt: off
        (CatalogRequirementFilterParams(), 0),
        #
        # filter by pattern
        (CatalogRequirementFilterParams(reference="ref*"), 1),
        (CatalogRequirementFilterParams(summary="sum*"), 1),
        (CatalogRequirementFilterParams(description="desc*"), 1),
        (CatalogRequirementFilterParams(gs_absicherung="gs_abs*"), 1),
        (CatalogRequirementFilterParams(gs_verantwortliche="gs_ver*"), 1),
        (CatalogRequirementFilterParams(reference="ref*", neg_reference=True), 1),
        (CatalogRequirementFilterParams(summary="sum*", neg_summary=True), 1),
        (CatalogRequirementFilterParams(description="desc*", neg_description=True), 1),
        (CatalogRequirementFilterParams(gs_absicherung="gs_abs*", neg_gs_absicherung=True), 1),
        (CatalogRequirementFilterParams(gs_verantwortliche="gs_ver*", neg_gs_verantwortliche=True), 1),
        #
        # filter by values
        (CatalogRequirementFilterParams(references=["ref1", "ref2"]), 1),
        (CatalogRequirementFilterParams(gs_absicherungen=["gs_abs1", "gs_abs2"]), 1),
        (CatalogRequirementFilterParams(references=["ref1", "ref2"], neg_references=True), 1),
        (CatalogRequirementFilterParams(gs_absicherungen=["gs_abs1", "gs_abs2"], neg_gs_absicherungen=True), 1),
        #
        # filter by ids
        (CatalogRequirementFilterParams(ids=[1, 2]), 1),
        (CatalogRequirementFilterParams(catalog_ids=[1, 2]), 1),
        (CatalogRequirementFilterParams(catalog_module_ids=[1, 2]), 1),
        (CatalogRequirementFilterParams(ids=[1, 2], neg_ids=True), 1),
        (CatalogRequirementFilterParams(catalog_ids=[1, 2], neg_catalog_ids=True), 1),
        (CatalogRequirementFilterParams(catalog_module_ids=[1, 2], neg_catalog_module_ids=True), 1),
        #
        # filter for existence
        (CatalogRequirementFilterParams(has_reference=True), 1),
        (CatalogRequirementFilterParams(has_description=True), 1),
        (CatalogRequirementFilterParams(has_gs_absicherung=True), 1),
        (CatalogRequirementFilterParams(has_gs_verantwortliche=True), 1),
        #
        # filter by search string
        (CatalogRequirementFilterParams(search="search"), 1),
        # fmt: on
    ],
)
def test_get_catalog_requirement_filters(
    params: CatalogRequirementFilterParams, expected_length: int
):
    filters = get_catalog_requirement_filters(**asdict(params))
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
