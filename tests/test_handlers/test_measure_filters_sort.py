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

from dataclasses import dataclass, asdict
from fastapi import HTTPException

import pytest

from mvtool.handlers.measures import get_measure_filters, get_measure_sort


@dataclass
class MeasureFilterParams:
    # filter by pattern
    reference: str | None = None
    summary: str | None = None
    description: str | None = None
    compliance_comment: str | None = None
    completion_comment: str | None = None
    verification_comment: str | None = None
    target_object: str | None = None
    milestone: str | None = None
    neg_reference: bool = False
    neg_summary: bool = False
    neg_description: bool = False
    neg_compliance_comment: bool = False
    neg_completion_comment: bool = False
    neg_verification_comment: bool = False
    neg_target_object: bool = False
    neg_milestone: bool = False
    #
    # filter by values
    references: list[str] | None = None
    compliance_statuses: list[str] | None = None
    completion_statuses: list[str] | None = None
    verification_statuses: list[str] | None = None
    verification_methods: list[str] | None = None
    target_objects: list[str] | None = None
    milestones: list[str] | None = None
    neg_references: bool = False
    neg_compliance_statuses: bool = False
    neg_completion_statuses: bool = False
    neg_verification_statuses: bool = False
    neg_verification_methods: bool = False
    neg_target_objects: bool = False
    neg_milestones: bool = False
    #
    # filter by ids
    ids: list[int] | None = None
    document_ids: list[int] | None = None
    jira_issue_ids: list[str] | None = None
    project_ids: list[int] | None = None
    requirement_ids: list[int] | None = None
    catalog_requirement_ids: list[int] | None = None
    catalog_module_ids: list[int] | None = None
    catalog_ids: list[int] | None = None
    neg_ids: bool = False
    neg_document_ids: bool = False
    neg_jira_issue_ids: bool = False
    neg_project_ids: bool = False
    neg_requirement_ids: bool = False
    neg_catalog_requirement_ids: bool = False
    neg_catalog_module_ids: bool = False
    neg_catalog_ids: bool = False
    #
    # filter for existence
    has_reference: bool | None = None
    has_description: bool | None = None
    has_compliance_status: bool | None = None
    has_compliance_comment: bool | None = None
    has_completion_status: bool | None = None
    has_completion_comment: bool | None = None
    has_verification_status: bool | None = None
    has_verification_method: bool | None = None
    has_verification_comment: bool | None = None
    has_document: bool | None = None
    has_jira_issue: bool | None = None
    has_catalog: bool | None = None
    has_catalog_module: bool | None = None
    has_catalog_requirement: bool | None = None
    has_target_object: bool | None = None
    has_milestone: bool | None = None
    #
    # filter by search string
    search: str | None = None


@pytest.mark.parametrize(
    "params, expected_length",
    [
        # fmt: off
        (MeasureFilterParams(), 0),
        #
        # filter by pattern
        (MeasureFilterParams(reference="ref*"), 1),
        (MeasureFilterParams(summary="sum*"), 1),
        (MeasureFilterParams(description="desc*"), 1),
        (MeasureFilterParams(compliance_comment="com*"), 1),
        (MeasureFilterParams(completion_comment="compl*"), 1),
        (MeasureFilterParams(verification_comment="ver*"), 1),
        (MeasureFilterParams(target_object="tar*"), 1),
        (MeasureFilterParams(milestone="mil*"), 1),
        (MeasureFilterParams(reference="ref*", neg_reference=True), 1),
        (MeasureFilterParams(summary="sum*", neg_summary=True), 1),
        (MeasureFilterParams(description="desc*", neg_description=True), 1),
        (MeasureFilterParams(compliance_comment="com*", neg_compliance_comment=True), 1),
        (MeasureFilterParams(completion_comment="compl*", neg_completion_comment=True), 1),
        (MeasureFilterParams(verification_comment="ver*", neg_verification_comment=True), 1),
        (MeasureFilterParams(target_object="tar*", neg_target_object=True), 1),
        (MeasureFilterParams(milestone="mil*", neg_milestone=True), 1),
        #
        # filter by values
        (MeasureFilterParams(references=["ref1", "ref2"]), 1),
        (MeasureFilterParams(compliance_statuses=["status1", "status2"]), 1),
        (MeasureFilterParams(completion_statuses=["status1", "status2"]), 1),
        (MeasureFilterParams(verification_statuses=["status1", "status2"]), 1),
        (MeasureFilterParams(verification_methods=["method1", "method2"]), 1),
        (MeasureFilterParams(target_objects=["object1", "object2"]), 1),
        (MeasureFilterParams(milestones=["milestone1", "milestone2"]), 1),

        (MeasureFilterParams(references=["ref1", "ref2"], neg_references=True), 1),
        (MeasureFilterParams(compliance_statuses=["status1", "status2"], neg_compliance_statuses=True), 1),
        (MeasureFilterParams(completion_statuses=["status1", "status2"], neg_completion_statuses=True), 1),
        (MeasureFilterParams(verification_statuses=["status1", "status2"], neg_verification_statuses=True), 1),
        (MeasureFilterParams(verification_methods=["method1", "method2"], neg_verification_methods=True), 1),
        (MeasureFilterParams(target_objects=["object1", "object2"], neg_target_objects=True), 1),
        (MeasureFilterParams(milestones=["milestone1", "milestone2"], neg_milestones=True), 1),
        #
        # filter by ids
        (MeasureFilterParams(ids=[1, 2]), 1),
        (MeasureFilterParams(document_ids=[1, 2]), 1),
        (MeasureFilterParams(jira_issue_ids=["JI-1", "JI-2"]), 1),
        (MeasureFilterParams(project_ids=[1, 2]), 1),
        (MeasureFilterParams(requirement_ids=[1, 2]), 1),
        (MeasureFilterParams(catalog_requirement_ids=[1, 2]), 1),
        (MeasureFilterParams(catalog_module_ids=[1, 2]), 1),
        (MeasureFilterParams(catalog_ids=[1, 2]), 1),
        (MeasureFilterParams(ids=[1, 2], neg_ids=True), 1),
        (MeasureFilterParams(document_ids=[1, 2], neg_document_ids=True), 1),
        (MeasureFilterParams(jira_issue_ids=["JI-1", "JI-2"], neg_jira_issue_ids=True), 1),
        (MeasureFilterParams(project_ids=[1, 2], neg_project_ids=True), 1),
        (MeasureFilterParams(requirement_ids=[1, 2], neg_requirement_ids=True), 1),
        (MeasureFilterParams(catalog_requirement_ids=[1, 2], neg_catalog_requirement_ids=True), 1),
        (MeasureFilterParams(catalog_module_ids=[1, 2], neg_catalog_module_ids=True), 1),
        (MeasureFilterParams(catalog_ids=[1, 2], neg_catalog_ids=True), 1),
        #
        # filter for existence
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
        #
        # filter by search string
        (MeasureFilterParams(search="search*"), 1),
        # fmt: on
    ],
)
def test_measure_filters(params: MeasureFilterParams, expected_length: int):
    filters = get_measure_filters(**asdict(params))
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
