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

from mvtool.handlers.projects import get_project_filters, get_project_sort


@dataclass
class ProjectFilterParams:
    # filter by pattern
    name: str = None
    description: str = None
    neg_name: bool = False
    neg_description: bool = False
    #
    # filter by values
    ids: list = None
    jira_project_ids: list = None
    neg_ids: bool = False
    neg_jira_project_ids: bool = False
    #
    # filter for existence
    has_description: bool = None
    has_jira_project: bool = None
    #
    # filter by search string
    search: str = None


@pytest.mark.parametrize(
    "params, expected_length",
    [
        (ProjectFilterParams(), 0),
        (ProjectFilterParams(name="name*"), 1),
        (ProjectFilterParams(description="description*"), 1),
        (ProjectFilterParams(name="name*", neg_name=True), 1),
        (ProjectFilterParams(description="description*", neg_description=True), 1),
        (ProjectFilterParams(ids=[1, 2]), 1),
        (ProjectFilterParams(jira_project_ids=["JP1", "JP2"]), 1),
        (ProjectFilterParams(has_description=True), 1),
        (ProjectFilterParams(has_jira_project=True), 1),
        (ProjectFilterParams(search="search"), 1),
    ],
)
def test_get_project_filters(params: ProjectFilterParams, expected_length: int):
    filters = get_project_filters(**asdict(params))
    assert isinstance(filters, list)
    assert len(filters) == expected_length


@pytest.mark.parametrize(
    "sort_by, sort_order, expected_length",
    [
        (None, None, 0),
        ("name", "asc", 2),
        ("name", "desc", 2),
        ("description", "asc", 2),
        ("description", "desc", 2),
        ("jira_project", "asc", 2),
        ("jira_project", "desc", 2),
    ],
)
def test_get_project_sort(sort_by, sort_order, expected_length):
    sort_clauses = get_project_sort(sort_by, sort_order)
    assert isinstance(sort_clauses, list)
    assert len(sort_clauses) == expected_length


def test_get_project_sort_invalid_sort_by():
    with pytest.raises(HTTPException) as exc_info:
        get_project_sort("invalid", "asc")
    assert exc_info.value.status_code == 400
    assert "Invalid sort_by parameter" in str(exc_info.value.detail)
