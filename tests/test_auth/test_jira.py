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

import pytest
from fastapi import HTTPException
from jira import JIRAError

from mvtool.auth.jira_ import authenticate_jira_user


def test_authenticate_jira_user(config):
    username, password, jira_config = ("user", "password", config.jira)
    with patch("mvtool.auth.jira_.JIRA") as jira_mock:
        authenticate_jira_user(username, password, jira_config)
        jira_mock.assert_called_once_with(
            jira_config.url,
            dict(verify=jira_config.verify_ssl),
            basic_auth=(username, password),
        )


def test_authenticate_jira_user_validate_credentials(config):
    username, password, jira_config = ("user", "password", config.jira)
    with patch("mvtool.auth.jira_.JIRA") as jira_mock:
        jira_mock.return_value = Mock()
        authenticate_jira_user(
            username, password, jira_config, validate_credentials=True
        )
        jira_mock.assert_called_once_with(
            jira_config.url,
            dict(verify=jira_config.verify_ssl),
            basic_auth=(username, password),
        )
        jira_mock.return_value.myself.assert_called_once()


def test_authenticate_jira_user_raise_jira_error(config):
    username, password, jira_config = ("user", "password", config.jira)
    with patch("mvtool.auth.jira_.JIRA") as jira_mock:
        jira_mock.side_effect = JIRAError("Jira error")
        with pytest.raises(HTTPException) as error_info:
            authenticate_jira_user(username, password, jira_config)
        assert "Jira error" in error_info.value.detail
