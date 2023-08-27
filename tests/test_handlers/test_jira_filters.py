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

from mvtool.handlers.jira_ import get_jira_issue_filters


@dataclass
class JiraIssueFilterParams:
    # Filter by values
    ids: list[str] | None = None
    keys: list[str] | None = None
    jira_project_ids: list[str] | None = None
    #
    # Filter by search string
    search: str | None = None


@pytest.mark.parametrize(
    "params, expected",
    [
        # fmt: off
        (JiraIssueFilterParams(), ""),
        (JiraIssueFilterParams(ids=["1"]), "id = 1"),
        (JiraIssueFilterParams(ids=["1", "2"]), "id IN (1, 2)"),
        (JiraIssueFilterParams(keys=["ABC"]), "key = ABC"),
        (JiraIssueFilterParams(keys=["ABC", "DEF"]), "key IN (ABC, DEF)"),
        (JiraIssueFilterParams(jira_project_ids=["1"]), "project = 1"),
        (JiraIssueFilterParams(jira_project_ids=["1", "2"]), "project IN (1, 2)"),
        (JiraIssueFilterParams(search="ABC"), '(text ~ "ABC*" OR key = "ABC")'),
        (JiraIssueFilterParams(ids=["1"], keys=["ABC"]), "id = 1 AND key = ABC"),
        (JiraIssueFilterParams(ids=["1"], search="ABC"), 'id = 1 AND (text ~ "ABC*" OR key = "ABC")'),
        # fmt: on
    ],
)
def test_get_jira_issue_filters(params, expected):
    assert get_jira_issue_filters(**asdict(params)) == expected
