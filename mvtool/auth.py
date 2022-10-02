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

import json
from threading import Lock
from jira import JIRA, JIRAError
from cachetools import TTLCache
from hashlib import sha256
from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from .errors import UnauthorizedError
from .utils.crypto import decrypt, encrypt
from .config import load_config, Config, JiraConfig

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

jira_connections_cache = TTLCache(maxsize=1000, ttl=5 * 60)
jira_connections_cache_lock = Lock()


def _get_jira_connection(username: str, password: str, jira_config: JiraConfig):
    cache_key = sha256(f"{username}:{password}".encode("utf-8")).hexdigest()
    with jira_connections_cache_lock:
        jira_connection = jira_connections_cache.get(cache_key, None)
    if jira_connection is None:
        jira_connection = JIRA(
            jira_config.url,
            dict(verify=jira_config.verify_ssl),
            basic_auth=(username, password),
        )
        with jira_connections_cache_lock:
            jira_connections_cache[cache_key] = jira_connection
    return jira_connection


def get_user_credentials(
    token: str = Depends(oauth2_scheme), config: Config = Depends(load_config)
):
    # decrypt user credentials from token and return it
    try:
        decrypted_token = decrypt(token, config.auth.derived_key)
    except InvalidToken as error:
        raise UnauthorizedError("Invalid token") from error
    return json.loads(decrypted_token)


def get_jira(
    credentials: dict = Depends(get_user_credentials),
    config: Config = Depends(load_config),
) -> JIRA:
    username, password = credentials
    try:
        yield _get_jira_connection(username, password, config.jira)
    except JIRAError as error:
        detail = None
        if error.text:
            detail = f"JIRAError: {error.text}"
        if error.url:
            detail += f" at url={error.url}"
        raise HTTPException(error.status_code, detail)


@router.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    config: Config = Depends(load_config),
):
    # check user credentials
    try:
        jira = _get_jira_connection(form_data.username, form_data.password, config.jira)
        jira.myself()
    except JIRAError as error:
        detail = None
        if error.text:
            detail = f"JIRAError: {error.text}"
        if error.url:
            detail += f" at url={error.url}"
        raise HTTPException(error.status_code, detail)

    # encrypt user credentials and return them as token
    token = encrypt(
        json.dumps((form_data.username, form_data.password)),
        load_config().auth.derived_key,
    )
    return {"access_token": token, "token_type": "bearer"}
