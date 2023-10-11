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

import pytest

from mvtool.config import (
    Config,
    DatabaseConfig,
    JiraConfig,
    LdapAttributeConfig,
    LdapConfig,
)


@pytest.mark.parametrize(
    "protocol, port_input, expected_port",
    [
        ("ldap", None, 389),
        ("ldaps", None, 636),
        ("ldap", 1234, 1234),
        ("ldaps", 1234, 1234),
    ],
)
def test_ldap_config_set_port_automatically(protocol, port_input, expected_port):
    data = {
        "host": "localhost",
        "protocol": protocol,
        "port": port_input,
        "base_dn": "dc=local",
        "attributes": LdapAttributeConfig(login="uid"),
    }
    config = LdapConfig(**data)
    assert config.port == expected_port


@pytest.mark.parametrize(
    "account_dn, account_password, should_raise",
    [
        (None, None, False),
        ("cn=admin,dc=local", "password", False),
        ("cn=admin,dc=local", None, True),
        (None, "password", False),
    ],
)
def test_ldap_config_account_password_must_be_set(
    account_dn, account_password, should_raise
):
    data = {
        "host": "localhost",
        "base_dn": "dc=local",
        "account_dn": account_dn,
        "account_password": account_password,
        "attributes": LdapAttributeConfig(login="uid"),
    }

    if should_raise:
        with pytest.raises(
            ValueError, match="account_password must be set when account_dn is set"
        ):
            LdapConfig(**data)
    else:
        config = LdapConfig(**data)
        assert config.account_dn == account_dn
        assert config.account_password == account_password


dummy_jira_config = JiraConfig(url="http://localhost/jira")
dummy_ldap_config = LdapConfig(
    host="localhost", base_dn="dc=local", attributes=LdapAttributeConfig(login="uid")
)


@pytest.mark.parametrize(
    "jira_config, ldap_config, should_raise",
    [
        (dummy_jira_config, None, False),  # Jira only
        (None, dummy_ldap_config, False),  # Ldap only
        (dummy_jira_config, dummy_ldap_config, False),  # Both Jira and Ldap
        (None, None, True),  # Neither Jira nor Ldap, should raise error
    ],
)
def test_config_at_least_one_service(jira_config, ldap_config, should_raise):
    data = {
        "database": DatabaseConfig(url="sqlite://"),
        "jira": jira_config,
        "ldap": ldap_config,
    }

    if should_raise:
        with pytest.raises(
            ValueError, match="At least one of jira or ldap must be set"
        ):
            Config(**data)
    else:
        config = Config(**data)
        assert config.jira == jira_config
        assert config.ldap == ldap_config
