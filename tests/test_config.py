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
