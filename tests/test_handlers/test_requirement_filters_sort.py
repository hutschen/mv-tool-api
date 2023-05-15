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
from fastapi import HTTPException
import pytest

from mvtool.handlers.requirements import get_requirement_filters, get_requirement_sort


@dataclass
class RequirementFilterParams:
    reference: str = None
    summary: str = None
    description: str = None
    gs_absicherung: str = None
    gs_verantwortliche: str = None
    target_object: str = None
    milestone: str = None
    compliance_comment: str = None
    references: list = None
    target_objects: list = None
    milestones: list = None
    compliance_statuses: list = None
    ids: list = None
    project_ids: list = None
    catalog_requirement_ids: list = None
    catalog_module_ids: list = None
    catalog_ids: list = None
    has_reference: bool = None
    has_description: bool = None
    has_target_object: bool = None
    has_milestone: bool = None
    has_compliance_status: bool = None
    has_compliance_comment: bool = None
    has_catalog: bool = None
    has_catalog_module: bool = None
    has_catalog_requirement: bool = None
    has_gs_absicherung: bool = None
    has_gs_verantwortliche: bool = None
    search: str = None


@pytest.mark.parametrize(
    "params, expected_length",
    [
        (RequirementFilterParams(), 0),
        (RequirementFilterParams(reference="ref*"), 1),
        (RequirementFilterParams(summary="title*"), 1),
        (RequirementFilterParams(description="desc*"), 1),
        (RequirementFilterParams(gs_absicherung="absicherung*"), 1),
        (RequirementFilterParams(gs_verantwortliche="verantwortliche*"), 1),
        (RequirementFilterParams(target_object="target*"), 1),
        (RequirementFilterParams(milestone="milestone*"), 1),
        (RequirementFilterParams(compliance_comment="comment*"), 1),
        (RequirementFilterParams(references=["ref1", "ref2"]), 1),
        (RequirementFilterParams(target_objects=["target1", "target2"]), 1),
        (RequirementFilterParams(milestones=["milestone1", "milestone2"]), 1),
        (RequirementFilterParams(compliance_statuses=["status1", "status2"]), 1),
        (RequirementFilterParams(ids=[1, 2]), 1),
        (RequirementFilterParams(project_ids=[1, 2]), 1),
        (RequirementFilterParams(catalog_requirement_ids=[1, 2]), 1),
        (RequirementFilterParams(catalog_module_ids=[1, 2]), 1),
        (RequirementFilterParams(catalog_ids=[1, 2]), 1),
        (RequirementFilterParams(has_reference=True), 1),
        (RequirementFilterParams(has_description=True), 1),
        (RequirementFilterParams(has_target_object=True), 1),
        (RequirementFilterParams(has_milestone=True), 1),
        (RequirementFilterParams(has_compliance_status=True), 1),
        (RequirementFilterParams(has_compliance_comment=True), 1),
        (RequirementFilterParams(has_catalog=True), 1),
        (RequirementFilterParams(has_catalog_module=True), 1),
        (RequirementFilterParams(has_catalog_requirement=True), 1),
        (RequirementFilterParams(has_gs_absicherung=True), 1),
        (RequirementFilterParams(has_gs_verantwortliche=True), 1),
        (RequirementFilterParams(search="search*"), 1),
    ],
)
def test_get_requirement_filters(params, expected_length):
    filters = get_requirement_filters(*astuple(params))
    assert isinstance(filters, list)
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
        ("target_object", "asc", 2),
        ("target_object", "desc", 2),
        ("milestone", "asc", 2),
        ("milestone", "desc", 2),
        ("project", "asc", 2),
        ("project", "desc", 2),
        ("catalog_requirement", "asc", 3),
        ("catalog_requirement", "desc", 3),
        ("catalog_module", "asc", 3),
        ("catalog_module", "desc", 3),
        ("catalog", "asc", 3),
        ("catalog", "desc", 3),
        ("compliance_status", "asc", 2),
        ("compliance_status", "desc", 2),
        ("compliance_comment", "asc", 2),
        ("compliance_comment", "desc", 2),
    ],
)
def test_get_requirement_sort(sort_by, sort_order, expected_length):
    sort_clauses = get_requirement_sort(sort_by, sort_order)
    assert isinstance(sort_clauses, list)
    assert len(sort_clauses) == expected_length


def test_get_requirement_sort_invalid_sort():
    with pytest.raises(HTTPException) as exc_info:
        get_requirement_sort(sort_by="invalid_sort_by", sort_order="asc")

    assert exc_info.value.status_code == 400
    assert "Invalid sort_by parameter" in str(exc_info.value.detail)
