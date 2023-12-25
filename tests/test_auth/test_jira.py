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

from unittest.mock import DEFAULT, Mock, patch

import pytest
from cryptography.fernet import InvalidToken
from fastapi import HTTPException
from jira import JIRAError

from mvtool.auth import get_jira, login_for_access_token
from mvtool.auth.cache import cache_session, get_cached_session
from mvtool.auth.jira_ import _connect_to_jira
from mvtool.auth.token import create_token, get_credentials_from_token


def test_connect_to_jira(config):
    username, password, jira_config = ("user", "password", config.jira)
    with patch("mvtool.auth.jira_.JIRA") as jira_mock:
        _connect_to_jira(username, password, jira_config)
        jira_mock.assert_called_once_with(
            jira_config.url,
            dict(verify=jira_config.verify_ssl),
            basic_auth=(username, password),
        )


def test_connect_to_jira_validate_credentials(config):
    username, password, jira_config = ("user", "password", config.jira)
    with patch("mvtool.auth.jira_.JIRA") as jira_mock:
        jira_mock.return_value = Mock()
        _connect_to_jira(username, password, jira_config, validate_credentials=True)
        jira_mock.assert_called_once_with(
            jira_config.url,
            dict(verify=jira_config.verify_ssl),
            basic_auth=(username, password),
        )
        jira_mock.return_value.myself.assert_called_once()


def test_connect_to_jira_raise_jira_error(config):
    username, password, jira_config = ("user", "password", config.jira)
    with patch("mvtool.auth.jira_.JIRA") as jira_mock:
        jira_mock.side_effect = JIRAError("Jira error")
        with pytest.raises(HTTPException) as error_info:
            _connect_to_jira(username, password, jira_config)
        assert "Jira error" in error_info.value.detail


def test_cache_jira():
    with patch("mvtool.auth.cache._sessions_cache", {}) as cache_mock:
        cache_session("token", None)
        assert len(cache_mock) == 1


def test_get_cached_jira():
    with patch("mvtool.auth.cache._sessions_cache", {}) as cache_mock:
        jira_mock = Mock()
        cache_session("token", jira_mock)
        assert len(cache_mock) == 1
        assert get_cached_session("token") is jira_mock


def test_get_cached_jira_fails():
    with patch("mvtool.auth.cache._sessions_cache", {}):
        assert get_cached_session("token") is None


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


def test_get_jira(config):
    with patch.multiple(
        "mvtool.auth",
        get_cached_session=DEFAULT,
        get_credentials_from_token=DEFAULT,
        _connect_to_jira_or_dummy_jira=DEFAULT,
        cache_session=DEFAULT,
    ) as mocks:
        mocks["get_cached_session"].return_value = None
        mocks["get_credentials_from_token"].return_value = ("user", "password")
        jira_mock = Mock()
        mocks["_connect_to_jira_or_dummy_jira"].return_value = jira_mock

        for result in get_jira("token", config):
            break

        assert result is jira_mock
        mocks["get_cached_session"].assert_called_once_with("token")
        mocks["get_credentials_from_token"].assert_called_once_with(
            "token", config.auth
        )
        mocks["_connect_to_jira_or_dummy_jira"].assert_called_once_with(
            "user", "password", config
        )
        mocks["cache_session"].assert_called_once_with("token", jira_mock)


def test_login_for_access_token(config):
    form_data_mock = Mock()
    form_data_mock.username = "user"
    form_data_mock.password = "password"

    with patch.multiple(
        "mvtool.auth",
        _connect_to_jira_or_dummy_jira=DEFAULT,
        create_token=DEFAULT,
        cache_session=DEFAULT,
    ) as mocks:
        mocks["create_token"].return_value = "token"
        jira_mock = Mock()
        mocks["_connect_to_jira_or_dummy_jira"].return_value = jira_mock

        result = login_for_access_token(form_data_mock, config)

        assert result == {"access_token": "token", "token_type": "bearer"}
        mocks["_connect_to_jira_or_dummy_jira"].assert_called_once_with(
            "user", "password", config, validate_credentials=True
        )
        mocks["create_token"].assert_called_once_with("user", "password", config.auth)
        mocks["cache_session"].assert_called_once_with("token", jira_mock)
