# coding: utf-8
#
# Copyright (C) 2022 Helmar Hutschenreuter
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

from threading import Lock
from jira import JIRA, JIRAError
from cachetools import TTLCache
from hashlib import sha256
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from .config import load_config

http_basic = HTTPBasic()
jira_connections_cache = TTLCache(maxsize=1000, ttl=5 * 60)
jira_connections_cache_lock = Lock()


def _get_jira(username, password):
    cache_key = sha256(f"{username}:{password}".encode("utf-8")).hexdigest()
    with jira_connections_cache_lock:
        jira_connection = jira_connections_cache.get(cache_key, None)
    if jira_connection is None:
        config = load_config().jira
        jira_connection = JIRA(
            config.url,
            dict(verify=config.verify_ssl),
            basic_auth=(username, password),
        )
        with jira_connections_cache_lock:
            jira_connections_cache[cache_key] = jira_connection
    return jira_connection


def get_jira(credentials: HTTPBasicCredentials = Depends(http_basic)) -> JIRA:
    try:
        yield _get_jira(credentials.username, credentials.password)
    except JIRAError as error:
        detail = None
        if error.text:
            detail = f"JIRAError: {error.text}"
        if error.url:
            detail += f" at url={error.url}"
        raise HTTPException(error.status_code, detail)
