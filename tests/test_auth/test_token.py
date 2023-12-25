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

from unittest.mock import patch

import pytest
from cryptography.fernet import InvalidToken
from fastapi import HTTPException

from mvtool.auth.token import create_token, get_credentials_from_token


def test_create_token(config):
    with patch("mvtool.auth.token.encrypt") as encrypt_mock:
        encrypt_mock.return_value = "encrypted"
        token = create_token("user", "password", config.auth)
        assert token == "encrypted"
        encrypt_mock.assert_called_once_with(
            '["user", "password"]', config.auth.derived_key
        )


def test_get_credentials_from_token(config):
    with patch("mvtool.auth.token.decrypt") as decrypt_mock:
        decrypt_mock.return_value = '["user", "password"]'
        username, password = get_credentials_from_token("token", config.auth)
        assert username == "user"
        assert password == "password"


def test_get_credentials_from_token_invalid_token(config):
    with patch("mvtool.auth.token.decrypt") as decrypt_mock:
        decrypt_mock.side_effect = InvalidToken()
        with pytest.raises(HTTPException) as error_info:
            get_credentials_from_token("token", config.auth)
        assert error_info.value.status_code == 401
