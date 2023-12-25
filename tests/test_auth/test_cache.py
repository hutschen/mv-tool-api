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

from unittest.mock import Mock, patch

from mvtool.auth.cache import cache_session, get_cached_session


def test_cache_jira():
    with patch("mvtool.auth.cache._sessions_cache", {}) as cache_mock:
        cache_session("token", None)
        assert len(cache_mock) == 1


def test_get_cached_jira():
    with patch("mvtool.auth.cache._sessions_cache", {}) as cache_mock:
        jira_mock = Mock()
        cache_session("token", jira_mock)
        assert len(cache_mock) == 1
        assert get_cached_session("token") is jira_mock


def test_get_cached_jira_fails():
    with patch("mvtool.auth.cache._sessions_cache", {}):
        assert get_cached_session("token") is None
