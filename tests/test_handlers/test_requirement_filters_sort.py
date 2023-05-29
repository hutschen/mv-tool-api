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
from fastapi import HTTPException
import pytest

from mvtool.handlers.requirements import get_requirement_filters, get_requirement_sort


@dataclass
class RequirementFilterParams:
    # filter by pattern
    reference: str | None = None
    summary: str | None = None
    description: str | None = None
    gs_absicherung: str | None = None
    gs_verantwortliche: str | None = None
    target_object: str | None = None
    milestone: str | None = None
    compliance_comment: str | None = None
    neg_reference: bool = False
    neg_summary: bool = False
    neg_description: bool = False
    neg_gs_absicherung: bool = False
    neg_gs_verantwortliche: bool = False
    neg_target_object: bool = False
    neg_milestone: bool = False
    neg_compliance_comment: bool = False
    #
    # filter by values
    references: list[str] | None = None
    target_objects: list[str] | None = None
    milestones: list[str] | None = None
    compliance_statuses: list[str] | None = None
    neg_references: bool = (False,)
    neg_target_objects: bool = (False,)
    neg_milestones: bool = (False,)
    neg_compliance_statuses: bool = (False,)
    #
    # filter by ids
    ids: list[int] | None = None
    project_ids: list[int] | None = None
    catalog_requirement_ids: list[int] | None = None
    catalog_module_ids: list[int] | None = None
    catalog_ids: list[int] | None = None
    neg_ids: bool = False
    neg_project_ids: bool = False
    neg_catalog_requirement_ids: bool = False
    neg_catalog_module_ids: bool = False
    neg_catalog_ids: bool = False
    #
    # filter for existence
    has_reference: bool | None = None
    has_description: bool | None = None
    has_target_object: bool | None = None
    has_milestone: bool | None = None
    has_compliance_status: bool | None = None
    has_compliance_comment: bool | None = None
    has_catalog: bool | None = None
    has_catalog_module: bool | None = None
    has_catalog_requirement: bool | None = None
    has_gs_absicherung: bool | None = None
    has_gs_verantwortliche: bool | None = None
    #
    # filter by search string
    search: str | None = None


@pytest.mark.parametrize(
    "params, expected_length",
    [
        # fmt: off
        (RequirementFilterParams(), 0),
        #
        # filter by pattern
        (RequirementFilterParams(reference="ref*"), 1),
        (RequirementFilterParams(summary="title*"), 1),
        (RequirementFilterParams(description="desc*"), 1),
        (RequirementFilterParams(gs_absicherung="absicherung*"), 1),
        (RequirementFilterParams(gs_verantwortliche="verantwortliche*"), 1),
        (RequirementFilterParams(target_object="target*"), 1),
        (RequirementFilterParams(milestone="milestone*"), 1),
        (RequirementFilterParams(compliance_comment="comment*"), 1),
        (RequirementFilterParams(reference="ref*", neg_reference=True), 1),
        (RequirementFilterParams(summary="title*", neg_summary=True), 1),
        (RequirementFilterParams(description="desc*", neg_description=True), 1),
        (RequirementFilterParams(gs_absicherung="absicherung*", neg_gs_absicherung=True), 1),
        (RequirementFilterParams(gs_verantwortliche="verantwortliche*", neg_gs_verantwortliche=True), 1),
        (RequirementFilterParams(target_object="target*", neg_target_object=True), 1),
        (RequirementFilterParams(milestone="milestone*", neg_milestone=True), 1),
        (RequirementFilterParams(compliance_comment="comment*", neg_compliance_comment=True), 1),
        #
        # filter by values
        (RequirementFilterParams(references=["ref1", "ref2"]), 1),
        (RequirementFilterParams(target_objects=["target1", "target2"]), 1),
        (RequirementFilterParams(milestones=["milestone1", "milestone2"]), 1),
        (RequirementFilterParams(compliance_statuses=["status1", "status2"]), 1),
        (RequirementFilterParams(references=["ref1", "ref2"], neg_references=True), 1),
        (RequirementFilterParams(target_objects=["target1", "target2"], neg_target_objects=True), 1),
        (RequirementFilterParams(milestones=["milestone1", "milestone2"], neg_milestones=True), 1),
        (RequirementFilterParams(compliance_statuses=["status1", "status2"], neg_compliance_statuses=True), 1),
        #
        # filter by ids
        (RequirementFilterParams(ids=[1, 2], neg_ids=True), 1),
        (RequirementFilterParams(project_ids=[1, 2], neg_project_ids=True), 1),
        (RequirementFilterParams(catalog_requirement_ids=[1, 2], neg_catalog_requirement_ids=True), 1),
        (RequirementFilterParams(catalog_module_ids=[1, 2], neg_catalog_module_ids=True), 1),
        (RequirementFilterParams(catalog_ids=[1, 2], neg_catalog_ids=True), 1),
        #
        # filter for existence
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
        #
        # filter by search string
        (RequirementFilterParams(search="search*"), 1),
        # fmt: on
    ],
)
def test_get_requirement_filters(params, expected_length):
    filters = get_requirement_filters(**asdict(params))
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
