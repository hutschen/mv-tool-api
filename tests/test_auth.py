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
from mvtool.auth import (
    _get_jira_connection,
    get_user_credentials,
    get_jira,
    login_for_access_token,
)


def test_get_jira_connection(config):
    username, password, jira_config = ("user", "password", config.jira)
    with patch("mvtool.auth.JIRA") as jira_mock:
        with patch("mvtool.auth.jira_connections_cache", {}) as cache_mock:
            _get_jira_connection(username, password, jira_config)
            jira_mock.assert_called_once_with(
                jira_config.url,
                dict(verify=jira_config.verify_ssl),
                basic_auth=(username, password),
            )
            assert len(cache_mock) == 1


def test_get_user_credentials(config):
    with patch("mvtool.auth.decrypt") as decrypt_mock:
        decrypt_mock.return_value = '["user", "password"]'
        username, password = get_user_credentials("token", config)
        assert username == "user"
        assert password == "password"


def test_get_jira(config):
    credentials = ("user", "password")
    with patch("mvtool.auth._get_jira_connection") as get_jira_connection_mock:
        for _ in get_jira(credentials, config):
            break
        get_jira_connection_mock.assert_called_once_with(*credentials, config.jira)


def test_login_for_access_token(config, jira):
    form_data_mock = Mock()
    form_data_mock.username = "user"
    form_data_mock.password = "password"

    with patch("mvtool.auth._get_jira_connection") as get_jira_connection_mock:
        get_jira_connection_mock.return_value = jira
        token = login_for_access_token(form_data_mock, config)
        assert isinstance(token, dict)
