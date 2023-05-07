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

from dataclasses import dataclass, astuple
from fastapi import HTTPException

import pytest

from mvtool.handlers.measures import get_measure_filters, get_measure_sort


@dataclass
class MeasureFilterParams:
    reference: str = None
    summary: str = None
    description: str = None
    compliance_comment: str = None
    completion_comment: str = None
    verification_comment: str = None
    target_object: str = None
    milestone: str = None
    references: list = None
    compliance_statuses: list = None
    completion_statuses: list = None
    verification_statuses: list = None
    verification_methods: list = None
    target_objects: list = None
    milestones: list = None
    ids: list = None
    document_ids: list = None
    jira_issue_ids: list = None
    project_ids: list = None
    requirement_ids: list = None
    catalog_requirement_ids: list = None
    catalog_module_ids: list = None
    catalog_ids: list = None
    has_reference: bool = None
    has_description: bool = None
    has_compliance_status: bool = None
    has_compliance_comment: bool = None
    has_completion_status: bool = None
    has_completion_comment: bool = None
    has_verification_status: bool = None
    has_verification_method: bool = None
    has_verification_comment: bool = None
    has_document: bool = None
    has_jira_issue: bool = None
    has_catalog: bool = None
    has_catalog_module: bool = None
    has_catalog_requirement: bool = None
    has_target_object: bool = None
    has_milestone: bool = None
    search: str = None


@pytest.mark.parametrize(
    "params, expected_length",
    [
        (MeasureFilterParams(), 0),
        (MeasureFilterParams(reference="ref*"), 1),
        (MeasureFilterParams(summary="sum*"), 1),
        (MeasureFilterParams(description="desc*"), 1),
        (MeasureFilterParams(compliance_comment="com*"), 1),
        (MeasureFilterParams(completion_comment="compl*"), 1),
        (MeasureFilterParams(verification_comment="ver*"), 1),
        (MeasureFilterParams(target_object="tar*"), 1),
        (MeasureFilterParams(milestone="mil*"), 1),
        (MeasureFilterParams(references=["ref1", "ref2"]), 1),
        (MeasureFilterParams(compliance_statuses=["status1", "status2"]), 1),
        (MeasureFilterParams(completion_statuses=["status1", "status2"]), 1),
        (MeasureFilterParams(verification_statuses=["status1", "status2"]), 1),
        (MeasureFilterParams(verification_methods=["method1", "method2"]), 1),
        (MeasureFilterParams(target_objects=["object1", "object2"]), 1),
        (MeasureFilterParams(milestones=["milestone1", "milestone2"]), 1),
        (MeasureFilterParams(ids=[1, 2]), 1),
        (MeasureFilterParams(document_ids=[1, 2]), 1),
        (MeasureFilterParams(jira_issue_ids=["JI-1", "JI-2"]), 1),
        (MeasureFilterParams(project_ids=[1, 2]), 1),
        (MeasureFilterParams(requirement_ids=[1, 2]), 1),
        (MeasureFilterParams(catalog_requirement_ids=[1, 2]), 1),
        (MeasureFilterParams(catalog_module_ids=[1, 2]), 1),
        (MeasureFilterParams(catalog_ids=[1, 2]), 1),
        (MeasureFilterParams(has_reference=True), 1),
        (MeasureFilterParams(has_description=True), 1),
        (MeasureFilterParams(has_compliance_status=True), 1),
        (MeasureFilterParams(has_compliance_comment=True), 1),
        (MeasureFilterParams(has_completion_status=True), 1),
        (MeasureFilterParams(has_completion_comment=True), 1),
        (MeasureFilterParams(has_verification_status=True), 1),
        (MeasureFilterParams(has_verification_method=True), 1),
        (MeasureFilterParams(has_verification_comment=True), 1),
        (MeasureFilterParams(has_document=True), 1),
        (MeasureFilterParams(has_jira_issue=True), 1),
        (MeasureFilterParams(has_catalog=True), 1),
        (MeasureFilterParams(has_catalog_module=True), 1),
        (MeasureFilterParams(has_catalog_requirement=True), 1),
        (MeasureFilterParams(has_target_object=True), 1),
        (MeasureFilterParams(has_milestone=True), 1),
        (MeasureFilterParams(search="search*"), 1),
    ],
)
def test_measure_filters(params: MeasureFilterParams, expected_length: int):
    filters = get_measure_filters(*astuple(params))
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
        ("compliance_status", "asc", 2),
        ("compliance_status", "desc", 2),
        ("compliance_comment", "asc", 2),
        ("compliance_comment", "desc", 2),
        ("completion_status", "asc", 2),
        ("completion_status", "desc", 2),
        ("completion_comment", "asc", 2),
        ("completion_comment", "desc", 2),
        ("verification_status", "asc", 2),
        ("verification_status", "desc", 2),
        ("verification_method", "asc", 2),
        ("verification_method", "desc", 2),
        ("verification_comment", "asc", 2),
        ("verification_comment", "desc", 2),
        ("document", "asc", 3),
        ("document", "desc", 3),
        ("jira_issue", "asc", 2),
        ("jira_issue", "desc", 2),
        ("requirement", "asc", 3),
        ("requirement", "desc", 3),
        ("catalog_requirement", "asc", 3),
        ("catalog_requirement", "desc", 3),
        ("catalog_module", "asc", 3),
        ("catalog_module", "desc", 3),
        ("catalog", "asc", 3),
        ("catalog", "desc", 3),
        ("target_object", "asc", 2),
        ("target_object", "desc", 2),
        ("milestone", "asc", 2),
        ("milestone", "desc", 2),
    ],
)
def test_get_measure_sort(sort_by, sort_order, expected_length):
    sort_clauses = get_measure_sort(sort_by, sort_order)
    assert isinstance(sort_clauses, list)
    assert len(sort_clauses) == expected_length


def test_get_measure_sort_invalid_sort_by():
    with pytest.raises(HTTPException) as exc_info:
        get_measure_sort("invalid", "asc")
    assert exc_info.value.status_code == 400
    assert "Invalid sort_by parameter" in str(exc_info.value.detail)
