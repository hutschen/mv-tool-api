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


from jira import JIRA, JIRAError
from cachetools import cached, TTLCache
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from .config import Config, load_config

http_basic = HTTPBasic()


@cached(cache=TTLCache(maxsize=1024, ttl=5 * 60))
def _get_jira(jira_server_url, username, password):
    return JIRA(jira_server_url, basic_auth=(username, password))


def get_jira(
    credentials: HTTPBasicCredentials = Depends(http_basic),
    config: Config = Depends(load_config),
) -> JIRA:
    try:
        yield _get_jira(config.jira.url, credentials.username, credentials.password)
    except JIRAError as error:
        detail = None
        if error.text:
            detail = f"JIRAError: {error.text}"
        if error.url:
            detail += f" at url={error.url}"
        raise HTTPException(error.status_code, detail)
