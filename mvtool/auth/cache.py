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
from hashlib import sha256
from threading import Lock

from cachetools import TTLCache
from jira import JIRA

_sessions_cache = TTLCache(maxsize=1000, ttl=5 * 60)
_sessions_cache_lock = Lock()


def cache_session(token: str, jira: JIRA):
    cache_key = sha256(token.encode("utf-8")).hexdigest()
    with _sessions_cache_lock:
        _sessions_cache[cache_key] = jira


def get_cached_session(token: str) -> JIRA | None:
    cache_key = sha256(token.encode("utf-8")).hexdigest()
    with _sessions_cache_lock:
        jira_connection = _sessions_cache.get(cache_key, None)
    return jira_connection
