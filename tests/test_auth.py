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

from unittest.mock import DEFAULT, Mock, patch
from fastapi import HTTPException
from cryptography.fernet import InvalidToken

from jira import JIRAError
import pytest
from mvtool.auth import (
    _cache_jira,
    _connect_to_jira,
    _create_token,
    _get_cached_jira,
    _get_credentials_from_token,
    get_jira,
    login_for_access_token,
)


def test_connect_to_jira(config):
    username, password, jira_config = ("user", "password", config.jira)
    with patch("mvtool.auth.JIRA") as jira_mock:
        _connect_to_jira(username, password, jira_config)
        jira_mock.assert_called_once_with(
            jira_config.url,
            dict(verify=jira_config.verify_ssl),
            basic_auth=(username, password),
        )


def test_connect_to_jira_validate_credentials(config):
    username, password, jira_config = ("user", "password", config.jira)
    with patch("mvtool.auth.JIRA") as jira_mock:
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
    with patch("mvtool.auth.JIRA") as jira_mock:
        jira_mock.side_effect = JIRAError("Jira error")
        with pytest.raises(HTTPException) as error_info:
            _connect_to_jira(username, password, jira_config)
        assert "Jira error" in error_info.value.detail


def test_cache_jira():
    with patch("mvtool.auth._jira_connections_cache", {}) as cache_mock:
        _cache_jira("token", None)
        assert len(cache_mock) == 1


def test_get_cached_jira():
    with patch("mvtool.auth._jira_connections_cache", {}) as cache_mock:
        jira_mock = Mock()
        _cache_jira("token", jira_mock)
        assert len(cache_mock) == 1
        assert _get_cached_jira("token") is jira_mock


def test_get_cached_jira_fails():
    with patch("mvtool.auth._jira_connections_cache", {}) as cache_mock:
        assert _get_cached_jira("token") is None


def test_create_token(config):
    with patch("mvtool.auth.encrypt") as encrypt_mock:
        encrypt_mock.return_value = "encrypted"
        token = _create_token("user", "password", config.auth)
        assert token == "encrypted"
        encrypt_mock.assert_called_once_with(
            '["user", "password"]', config.auth.derived_key
        )


def test_get_credentials_from_token(config):
    with patch("mvtool.auth.decrypt") as decrypt_mock:
        decrypt_mock.return_value = '["user", "password"]'
        username, password = _get_credentials_from_token("token", config.auth)
        assert username == "user"
        assert password == "password"


def test_get_credentials_from_token_invalid_token(config):
    with patch("mvtool.auth.decrypt") as decrypt_mock:
        decrypt_mock.side_effect = InvalidToken()
        with pytest.raises(HTTPException) as error_info:
            _get_credentials_from_token("token", config.auth)
        assert error_info.value.status_code == 401


def test_get_jira(config):
    with patch.multiple(
        "mvtool.auth",
        _get_cached_jira=DEFAULT,
        _get_credentials_from_token=DEFAULT,
        _connect_to_jira=DEFAULT,
        _cache_jira=DEFAULT,
    ) as mocks:
        mocks["_get_cached_jira"].return_value = None
        mocks["_get_credentials_from_token"].return_value = ("user", "password")
        jira_mock = Mock()
        mocks["_connect_to_jira"].return_value = jira_mock

        for result in get_jira("token", config):
            break

        assert result is jira_mock
        mocks["_get_cached_jira"].assert_called_once_with("token")
        mocks["_get_credentials_from_token"].assert_called_once_with(
            "token", config.auth
        )
        mocks["_connect_to_jira"].assert_called_once_with(
            "user", "password", config.jira
        )
        mocks["_cache_jira"].assert_called_once_with("token", jira_mock)


def test_login_for_access_token(config):
    form_data_mock = Mock()
    form_data_mock.username = "user"
    form_data_mock.password = "password"

    with patch.multiple(
        "mvtool.auth",
        _connect_to_jira=DEFAULT,
        _create_token=DEFAULT,
        _cache_jira=DEFAULT,
    ) as mocks:
        mocks["_create_token"].return_value = "token"
        jira_mock = Mock()
        mocks["_connect_to_jira"].return_value = jira_mock

        result = login_for_access_token(form_data_mock, config)

        assert result == {"access_token": "token", "token_type": "bearer"}
        mocks["_connect_to_jira"].assert_called_once_with(
            "user", "password", config.jira, validate_credentials=True
        )
        mocks["_create_token"].assert_called_once_with("user", "password", config.auth)
        mocks["_cache_jira"].assert_called_once_with("token", jira_mock)
