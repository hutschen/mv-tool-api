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

from mvtool.auth_ldap import authenticate_ldap_user
from mvtool.config import Config
from mvtool.utils.errors import ClientError, UnauthorizedError


@pytest.fixture
def ldap_initialize_mock():
    with patch("ldap.initialize") as mock_initialize:
        yield mock_initialize


def test_ssl_verification_disabled(ldap_initialize_mock, config: Config):
    config.ldap.verify_ssl = False
    authenticate_ldap_user("jdoe", "password", config.ldap)
    ldap_conn_mock = ldap_initialize_mock.return_value
    ldap_conn_mock.set_option.assert_called_with(
        ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER
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
    ldap_conn_mock.set_option.assert_called_with(
        ldap.OPT_X_TLS_CACERTFILE, "/path/to/cert"
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
