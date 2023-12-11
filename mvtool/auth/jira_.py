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

from hashlib import sha256
from threading import Lock

from cachetools import TTLCache
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jira import JIRA, JIRAError

from ..config import Config, JiraConfig, load_config
from .token import create_token, get_credentials_from_token
from .ldap_ import LdapJiraDummy, authenticate_ldap_user

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

_jira_connections_cache = TTLCache(maxsize=1000, ttl=5 * 60)
_jira_connections_cache_lock = Lock()


def _connect_to_jira(
    username: str,
    password: str,
    jira_config: JiraConfig,
    validate_credentials: bool = False,
) -> JIRA:
    try:
        jira_connection = JIRA(
            jira_config.url,
            dict(verify=jira_config.verify_ssl),
            basic_auth=(username, password),
        )
        if validate_credentials:
            jira_connection.myself()
    except JIRAError as error:
        detail = None
        if error.text:
            detail = f"JIRAError: {error.text}"
        if error.url:
            detail += f" at url={error.url}"
        raise HTTPException(error.status_code, detail)
    return jira_connection


# FIXME: Remove this function when LDAP integration is fully implemented.
def _connect_to_jira_or_dummy_jira(
    username: str, password: str, config: Config, validate_credentials: bool = False
) -> JIRA | LdapJiraDummy:
    """
    This function is a temporary solution for the quick integration of LDAP. If LDAP is
    configured, an attempt is first made to connect to LDAP. If this fails, a connection
    to JIRA is established. Either a JIRA connection or a JIRA dummy connection is
    returned. The latter simulates a JIRA connection, allowing LDAP to be used without
    requiring changes elsewhere in the code.
    """

    # LDAP is disabled, so connect to JIRA directly
    if config.ldap is None:
        return _connect_to_jira(username, password, config.jira, validate_credentials)

    # LDAP is enabled, so try to connect to LDAP first
    try:
        return LdapJiraDummy(authenticate_ldap_user(username, password, config.ldap))
    except HTTPException as error:
        # LDAP connection failed, so try to connect to JIRA if JIRA is enabled
        if config.jira is None:
            raise error
        return _connect_to_jira(username, password, config.jira, validate_credentials)


def _cache_jira(token: str, jira: JIRA):
    cache_key = sha256(token.encode("utf-8")).hexdigest()
    with _jira_connections_cache_lock:
        _jira_connections_cache[cache_key] = jira


def _get_cached_jira(token: str) -> JIRA | None:
    cache_key = sha256(token.encode("utf-8")).hexdigest()
    with _jira_connections_cache_lock:
        jira_connection = _jira_connections_cache.get(cache_key, None)
    return jira_connection


def get_jira(
    token: str = Depends(oauth2_scheme), config: Config = Depends(load_config)
) -> JIRA:
    # get jira connection from cache or create new one
    jira_connection = _get_cached_jira(token)
    if jira_connection is None:
        username, password = get_credentials_from_token(token, config.auth)
        jira_connection = _connect_to_jira_or_dummy_jira(username, password, config)
        _cache_jira(token, jira_connection)

    # yield jira_connection to catch JIRA errors
    try:
        yield jira_connection
    except JIRAError as error:
        details = [
            error.text,
            error.response.text if error.response is not None else None,
            error.url,
        ]
        details_str = "; ".join([d for d in details if d]) or "Unknown error"
        raise HTTPException(error.status_code, detail=f"JIRAError: {details_str}")


@router.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    config: Config = Depends(load_config),
):
    # check user credentials
    jira_connection = _connect_to_jira_or_dummy_jira(
        form_data.username, form_data.password, config, validate_credentials=True
    )
    token = create_token(form_data.username, form_data.password, config.auth)
    _cache_jira(token, jira_connection)
    return {"access_token": token, "token_type": "bearer"}
