# coding: utf-8
# 
# Copyright 2022 Helmar Hutschenreuter
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation. You may obtain
# a copy of the GNU AGPL V3 at https://www.gnu.org/licenses/.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AGPL V3 for more details.

from jira import JIRA, JIRAError
from cachetools import cached, TTLCache
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from .config import Config, load_config

http_basic = HTTPBasic()

@cached(cache=TTLCache(maxsize=1024, ttl=5*60))
def _get_jira(jira_server_url, username, password):
    return JIRA(jira_server_url, basic_auth=(username, password))

def get_jira(
        credentials: HTTPBasicCredentials = Depends(http_basic),
        config: Config = Depends(load_config)) -> JIRA:
    try:
        yield _get_jira(
            config.jira_server_url, credentials.username, credentials.password)
    except JIRAError as error:
        detail = None
        if error.text:
            detail = f'JIRAError: {error.text}'
        if error.url:
            detail += f' at url={error.url}'
        raise HTTPException(error.status_code, detail)