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

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jira import JIRA, JIRAError

from ..config import Config, load_config
from .cache import cache_session, get_cached_session
from .jira_ import _connect_to_jira_or_dummy_jira
from .token import create_token, get_credentials_from_token

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


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
    cache_session(token, jira_connection)
    return {"access_token": token, "token_type": "bearer"}


def get_jira(
    token: str = Depends(oauth2_scheme), config: Config = Depends(load_config)
) -> JIRA:
    # get jira connection from cache or create new one
    jira_connection = get_cached_session(token)
    if jira_connection is None:
        username, password = get_credentials_from_token(token, config.auth)
        jira_connection = _connect_to_jira_or_dummy_jira(username, password, config)
        cache_session(token, jira_connection)

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
