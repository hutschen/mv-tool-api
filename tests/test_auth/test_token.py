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
from unittest.mock import patch

import pytest
from cryptography.fernet import InvalidToken
from fastapi import HTTPException

from mvtool.auth.token import create_token, get_credentials_from_token
from mvtool.config import Config


@pytest.mark.parametrize(
    "timestamp, ttl, expected_expiration",
    [
        (1234567890, 3600, 1234567890 + 3600),
        (1234567890.123, 3600, 1234567890 + 3600),
        (1234567890, 0, None),
        (1234567890, -1, None),
        (1234567890, None, None),
    ],
)
def test_create_token(timestamp, ttl, expected_expiration, config: Config):
    config.auth.ttl = ttl

    with (
        patch("mvtool.auth.token.encrypt") as encrypt_mock,
        patch("time.time", return_value=timestamp),
    ):
        encrypt_mock.return_value = "encrypted"
        print(config.auth.ttl)
        token = create_token("user", "password", config.auth)

        assert token == "encrypted"
        encrypt_mock.assert_called_once_with(
            json.dumps(["user", "password", expected_expiration]),
            config.auth.derived_key,
        )


@pytest.mark.parametrize(
    "timestamp, expiration_time",
    [
        (1234567890, 1234567890 + 3600),
        (1234567890, None),
        (1234567890, 0),
    ],
)
def test_get_credentials_from_unexpired_token(timestamp, expiration_time, config):
    with (
        patch("mvtool.auth.token.decrypt") as decrypt_mock,
        patch("time.time", return_value=timestamp),
    ):
        decrypt_mock.return_value = json.dumps(["user", "password", expiration_time])
        username, password = get_credentials_from_token("token", config.auth)
        assert username == "user"
        assert password == "password"


@pytest.mark.parametrize(
    "timestamp, expiration_time",
    [
        (1234567890, 1234567890 - 3600),
        (1234567890, -1),
    ],
)
def test_get_credentials_from_token_expired_token(timestamp, expiration_time, config):
    with (
        patch("mvtool.auth.token.decrypt") as decrypt_mock,
        patch("time.time", return_value=timestamp),
    ):
        decrypt_mock.return_value = json.dumps(["user", "password", expiration_time])
        with pytest.raises(HTTPException) as error_info:
            get_credentials_from_token("token", config.auth)
        assert error_info.value.status_code == 401


def test_get_credentials_from_token_invalid_token(config):
    with patch("mvtool.auth.token.decrypt") as decrypt_mock:
        decrypt_mock.side_effect = InvalidToken()
        with pytest.raises(HTTPException) as error_info:
            get_credentials_from_token("token", config.auth)
        assert error_info.value.status_code == 401
