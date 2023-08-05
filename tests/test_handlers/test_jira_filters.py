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

from mvtool.handlers.jira_ import get_jira_issue_filters


@pytest.mark.parametrize(
    "params, expected",
    [
        # fmt: off
        (dict(), ""),
        (dict(key="KEY-1"), "key = KEY-1"),
        (dict(jira_project_id="PROJECT-1"), "project = PROJECT-1"),
        (dict(key="KEY-1", jira_project_id="PROJECT-1"), "key = KEY-1 AND project = PROJECT-1"),
        (dict(search="search"), 'text ~ "search"'),
        (dict(key="KEY-1", search="search"), 'key = KEY-1 AND text ~ "search"'),
        # fmt: on
    ],
)
def test_get_jira_issue_filters(params, expected):
    assert get_jira_issue_filters(**params) == expected
