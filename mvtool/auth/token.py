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

import json
import time

from cryptography.fernet import InvalidToken

from ..config import AuthConfig
from ..utils.crypto import decrypt, encrypt
from ..utils.errors import UnauthorizedError


def create_token(username: str, password: str, auth_config: AuthConfig) -> str:
    expiration_time = (
        int(time.time()) + auth_config.ttl
        if auth_config.ttl and 0 < auth_config.ttl
        else None
    )
    return encrypt(
        json.dumps([username, password, expiration_time]),
        auth_config.derived_key,
    )


def get_credentials_from_token(token: str, auth_config: AuthConfig) -> tuple[str, str]:
    try:
        decrypted_token = decrypt(token, auth_config.derived_key)
    except InvalidToken as error:
        raise UnauthorizedError("Invalid token") from error
    username, password, expiration_time = json.loads(decrypted_token)
    if expiration_time and expiration_time < int(time.time()):
        raise UnauthorizedError("Token expired")
    return username, password
