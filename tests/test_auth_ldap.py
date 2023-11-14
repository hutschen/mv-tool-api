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

from unittest.mock import Mock, call, patch

import ldap
import pytest
from jira import JIRAError

from mvtool.auth_ldap import LdapJiraDummy, LdapUserDetails, authenticate_ldap_user
from mvtool.config import Config
from mvtool.utils.errors import ClientError, UnauthorizedError


@pytest.fixture
def ldap_initialize_mock():
    with patch("ldap.initialize") as mock_initialize:
        yield mock_initialize


@pytest.mark.parametrize(
    "user_details_kwargs, expected_display_name",
    [
        ({"login": "jdoe", "firstname": "John", "lastname": "Doe"}, "John Doe"),
        ({"login": "jdoe", "email": "johndoe@local"}, "johndoe@local"),
        ({"login": "jdoe", "firstname": "John"}, "jdoe"),
        ({"login": "jdoe", "lastname": "Doe"}, "jdoe"),
        ({"login": "jdoe"}, "jdoe"),
    ],
)
def test_ldap_user_details_display_name(user_details_kwargs, expected_display_name):
    user_details = LdapUserDetails(**user_details_kwargs)
    assert user_details.display_name == expected_display_name


def test_ssl_verification_disabled(ldap_initialize_mock, config: Config):
    config.ldap.verify_ssl = False
    authenticate_ldap_user("jdoe", "password", config.ldap)
    ldap_conn_mock = ldap_initialize_mock.return_value
    ldap_conn_mock.set_option.assert_has_calls(
        [
            call(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER),
            call(ldap.OPT_X_TLS_NEWCTX, 0),
        ]
    )


def test_ssl_verification_enabled(ldap_initialize_mock, config: Config):
    config.ldap.verify_ssl = True
    authenticate_ldap_user("jdoe", "password", config.ldap)
    ldap_conn_mock = ldap_initialize_mock.return_value
    ldap_conn_mock.set_option.assert_not_called()


def test_ssl_cert_path(ldap_initialize_mock, config: Config):
    config.ldap.verify_ssl = "/path/to/cert"
    authenticate_ldap_user("jdoe", "password", config.ldap)
    ldap_conn_mock = ldap_initialize_mock.return_value
    ldap_conn_mock.set_option.assert_has_calls(
        [
            call(ldap.OPT_X_TLS_CACERTFILE, "/path/to/cert"),
            call(ldap.OPT_X_TLS_NEWCTX, 0),
        ]
    )


def test_with_account_dn(ldap_initialize_mock, config: Config):
    ldap_conn_mock = Mock()
    ldap_conn_mock.search_s.return_value = [
        ("uid=jdoe,ou=people,dc=local", {"uid": [b"jdoe"]})
    ]
    ldap_initialize_mock.return_value = ldap_conn_mock

    config.ldap.account_dn = "cn=admin,dc=local"
    config.ldap.account_password = "admin_password"

    authenticate_ldap_user("jdoe", "password", config.ldap)

    # Check if simple_bind_s is called twice with the expected arguments
    assert ldap_conn_mock.simple_bind_s.call_count == 2
    calls = [
        call("cn=admin,dc=local", "admin_password"),
        call("uid=jdoe,ou=people,dc=local", "password"),
    ]
    ldap_conn_mock.simple_bind_s.assert_has_calls(calls)


def test_without_account_dn(ldap_initialize_mock, config: Config):
    ldap_conn_mock = Mock()
    ldap_conn_mock.search_s.return_value = [
        ("uid=jdoe,ou=people,dc=local", {"uid": [b"jdoe"]})
    ]
    ldap_initialize_mock.return_value = ldap_conn_mock
    config.ldap.account_dn = None
    config.ldap.account_password = None

    authenticate_ldap_user("jdoe", "password", config.ldap)

    # Check if simple_bind_s is called only once with the expected arguments
    assert ldap_conn_mock.simple_bind_s.call_count == 1
    ldap_conn_mock.simple_bind_s.assert_called_with(
        "uid=jdoe,ou=people,dc=local", "password"
    )


def test_invalid_credentials(ldap_initialize_mock, config: Config):
    ldap_conn_mock = Mock()
    ldap_conn_mock.search_s.return_value = [
        ("uid=jdoe,ou=people,dc=local", {"uid": [b"jdoe"]})
    ]
    ldap_initialize_mock.return_value = ldap_conn_mock

    # Set account_dn and account_password to None call simple_bind_s only once
    config.ldap.account_dn = None
    config.ldap.account_password = None

    # Let simple_bind_s raise an exception
    ldap_conn_mock.simple_bind_s.side_effect = ldap.INVALID_CREDENTIALS

    with pytest.raises(UnauthorizedError, match="Invalid credentials"):
        authenticate_ldap_user("jdoe", "wrong_password", config.ldap)

    # Check if simple_bind_s is called only once with the expected arguments
    assert ldap_conn_mock.simple_bind_s.call_count == 1
    ldap_conn_mock.simple_bind_s.assert_called_with(
        "uid=jdoe,ou=people,dc=local", "wrong_password"
    )


def test_authenticate_ldap_user_invalid(ldap_initialize_mock, config: Config):
    ldap_conn_mock = Mock()
    ldap_conn_mock.search_s.return_value = []
    ldap_initialize_mock.return_value = ldap_conn_mock

    with pytest.raises(UnauthorizedError) as error_info:
        authenticate_ldap_user("invalid", "password", config.ldap)
    assert error_info.value.detail == "User not found"


def test_authenticate_ldap_user_ldap_error(ldap_initialize_mock, config: Config):
    ldap_conn_mock = Mock()
    ldap_conn_mock.search_s.side_effect = ldap.LDAPError("Something went wrong")
    ldap_initialize_mock.return_value = ldap_conn_mock

    with pytest.raises(ClientError) as error_info:
        authenticate_ldap_user("jdoe", "password", config.ldap)
    assert "Error searching the LDAP directory" in error_info.value.detail


def test_ldap_jira_dummy_myself():
    ldap_details = LdapUserDetails(
        login="jdoe", firstname="John", lastname="Doe", email="johndoe@local"
    )
    jira_dummy = LdapJiraDummy(ldap_details)
    myself_result = jira_dummy.myself()

    assert myself_result["accountId"] == "jdoe"
    assert myself_result["displayName"] == "John Doe"
    assert myself_result["emailAddress"] == "johndoe@local"


def test_ldap_jira_dummy_user_found():
    ldap_details = LdapUserDetails(login="jdoe")
    jira_dummy = LdapJiraDummy(ldap_details)
    user_result = jira_dummy.user("jdoe")

    assert user_result["accountId"] == "jdoe"


def test_ldap_jira_dummy_user_not_found():
    ldap_details = LdapUserDetails(login="jdoe")
    jira_dummy = LdapJiraDummy(ldap_details)

    with pytest.raises(JIRAError, match="User not found"):
        jira_dummy.user("other_user")


def test_ldap_jira_dummy_projects():
    ldap_details = LdapUserDetails(login="jdoe")
    jira_dummy = LdapJiraDummy(ldap_details)
    assert jira_dummy.projects() == []


def test_ldap_jira_dummy_project():
    ldap_details = LdapUserDetails(login="jdoe")
    jira_dummy = LdapJiraDummy(ldap_details)

    with pytest.raises(JIRAError, match="Project not found"):
        jira_dummy.project(1)


def test_ldap_jira_dummy_search_issues():
    ldap_details = LdapUserDetails(login="jdoe")
    jira_dummy = LdapJiraDummy(ldap_details)
    assert jira_dummy.search_issues() == []


def test_ldap_jira_dummy_create_issue():
    ldap_details = LdapUserDetails(login="jdoe")
    jira_dummy = LdapJiraDummy(ldap_details)

    with pytest.raises(JIRAError, match="Cannot create issue"):
        jira_dummy.create_issue()


def test_ldap_jira_dummy_issue_method():
    ldap_details = LdapUserDetails(login="jdoe")
    jira_dummy = LdapJiraDummy(ldap_details)

    with pytest.raises(JIRAError, match="Issue not found"):
        jira_dummy.issue(1)
