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

from unittest.mock import DEFAULT, Mock, patch

from mvtool.auth import get_jira, login_for_access_token


def test_get_jira(config):
    with patch.multiple(
        "mvtool.auth",
        get_cached_session=DEFAULT,
        get_credentials_from_token=DEFAULT,
        _authenticate_user=DEFAULT,
        cache_session=DEFAULT,
    ) as mocks:
        mocks["get_cached_session"].return_value = None
        mocks["get_credentials_from_token"].return_value = ("user", "password")
        jira_mock = Mock()
        mocks["_authenticate_user"].return_value = jira_mock

        for result in get_jira("token", config):
            break

        assert result is jira_mock
        mocks["get_cached_session"].assert_called_once_with("token")
        mocks["get_credentials_from_token"].assert_called_once_with(
            "token", config.auth
        )
        mocks["_authenticate_user"].assert_called_once_with("user", "password", config)
        mocks["cache_session"].assert_called_once_with("token", jira_mock)


def test_login_for_access_token(config):
    form_data_mock = Mock()
    form_data_mock.username = "user"
    form_data_mock.password = "password"

    with patch.multiple(
        "mvtool.auth",
        _authenticate_user=DEFAULT,
        create_token=DEFAULT,
        cache_session=DEFAULT,
    ) as mocks:
        mocks["create_token"].return_value = "token"
        jira_mock = Mock()
        mocks["_authenticate_user"].return_value = jira_mock

        result = login_for_access_token(form_data_mock, config)

        assert result == {"access_token": "token", "token_type": "bearer"}
        mocks["_authenticate_user"].assert_called_once_with(
            "user", "password", config, validate_credentials=True
        )
        mocks["create_token"].assert_called_once_with("user", "password", config.auth)
        mocks["cache_session"].assert_called_once_with("token", jira_mock)
