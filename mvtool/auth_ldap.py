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

from dataclasses import dataclass

import ldap
from jira import JIRAError

from .config import LdapConfig
from .utils.errors import ClientError, UnauthorizedError


@dataclass
class LdapUserDetails:
    login: str
    firstname: str | None
    lastname: str | None
    email: str | None


def authenticate_ldap_user(username: str, password: str, ldap_config: LdapConfig):
    # Connect to LDAP server
    uri = f"{ldap_config.protocol}://{ldap_config.host}:{ldap_config.port}"
    conn = ldap.initialize(uri)

    # Handle SSL verification
    if ldap_config.verify_ssl == False:
        conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    elif isinstance(ldap_config.verify_ssl, str):
        conn.set_option(ldap.OPT_X_TLS_CACERTFILE, ldap_config.verify_ssl)

    # Bind account if account_dn is provided
    if ldap_config.account_dn and ldap_config.account_password:
        conn.simple_bind_s(ldap_config.account_dn, ldap_config.account_password)

    # Search for user
    search_filter = (
        f"(&({ldap_config.attributes.login}={username}){ldap_config.user_filter or ''})"
    )
    attributes = [
        attribute
        for attribute in [
            ldap_config.attributes.login,
            ldap_config.attributes.firstname,
            ldap_config.attributes.lastname,
            ldap_config.attributes.email,
        ]
        if attribute is not None
    ]

    try:
        result = conn.search_s(
            ldap_config.base_dn, ldap.SCOPE_SUBTREE, search_filter, attributes
        )
    except ldap.LDAPError as e:
        raise ClientError(f"Error searching the LDAP directory: {e}")

    if not result:
        raise UnauthorizedError("User not found")

    # Bind as user to check credentials
    user_dn = result[0][0]
    try:
        conn.simple_bind_s(user_dn, password)
    except ldap.INVALID_CREDENTIALS:
        raise UnauthorizedError("Invalid credentials")

    # Return user details
    user_info = result[0][1]
    return LdapUserDetails(
        login=user_info.get(ldap_config.attributes.login, [None])[0],
        firstname=user_info.get(ldap_config.attributes.firstname, [None])[0],
        lastname=user_info.get(ldap_config.attributes.lastname, [None])[0],
        email=user_info.get(ldap_config.attributes.email, [None])[0],
    )


# FIXME: Remove this dummy class when LDAP integration is fully implemented.
class LdapJiraDummy:
    """
    This class serves as a dummy to simulate an LDAP user as a JIRA user. It is used
    because the LDAP integration is not yet fully implemented and serves as a
    workaround. The full LDAP integration will be added in a later release.
    """

    def __init__(self, ldap_user_details: LdapUserDetails):
        self.server_url = "http://dummy-url"
        self._is_cloud = False
        self.__ldap_user_details = ldap_user_details

    def myself(self):
        return dict(
            accountId=self.__ldap_user_details.login,
            displayName=self.__ldap_user_details.login,
            emailAddress=self.__ldap_user_details.email,
        )

    def user(self, id):
        if id == self.__ldap_user_details.login:
            return self.myself()
        else:
            raise JIRAError("User not found", 404)

    def projects(self):
        return []

    def project(self, id):
        raise JIRAError("Project not found", 404)

    def search_issues(*args, **kwargs):
        return []

    def create_issue(*args, **kwargs):
        raise JIRAError("Cannot create issue", 500)

    def issue(self, id):
        raise JIRAError("Issue not found", 404)
