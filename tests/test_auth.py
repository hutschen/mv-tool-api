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

from unittest.mock import Mock, patch
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


@pytest.mark.skip("TODO")
def test_get_jira(config):
    pass


@pytest.mark.skip("TODO")
def test_login_for_access_token(config, jira):
    form_data_mock = Mock()
    form_data_mock.username = "user"
    form_data_mock.password = "password"

    with patch("mvtool.auth._get_jira_connection") as get_jira_connection_mock:
        get_jira_connection_mock.return_value = jira
        token = login_for_access_token(form_data_mock, config)
        assert isinstance(token, dict)
