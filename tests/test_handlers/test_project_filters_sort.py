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

from mvtool.handlers.projects import get_project_filters, get_project_sort


@pytest.mark.parametrize(
    "name, description, ids, jira_project_ids, has_description, has_jira_project, search, expected_length",
    [
        (None, None, None, None, None, None, None, 0),
        ("name*", None, None, None, None, None, None, 1),
        (None, "description*", None, None, None, None, None, 1),
        (None, None, [1, 2], None, None, None, None, 1),
        (None, None, None, ["JP1", "JP2"], None, None, None, 1),
        (None, None, None, None, True, None, None, 1),
        (None, None, None, None, None, True, None, 1),
        (None, None, None, None, None, None, "search", 1),
    ],
)
def test_get_project_filters(
    name,
    description,
    ids,
    jira_project_ids,
    has_description,
    has_jira_project,
    search,
    expected_length,
):
    filters = get_project_filters(
        name,
        description,
        ids,
        jira_project_ids,
        has_description,
        has_jira_project,
        search,
    )
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
