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


from fastapi import HTTPException
from jira import JIRA, JIRAError

from ..config import Config, JiraConfig
from .ldap_ import LdapJiraDummy, authenticate_ldap_user


def authenticate_jira_user(
    username: str,
    password: str,
    jira_config: JiraConfig,
    validate_credentials: bool = False,
) -> JIRA:
    try:
        jira_connection = JIRA(
            jira_config.url,
            dict(verify=jira_config.verify_ssl),
            basic_auth=(username, password),
        )
        if validate_credentials:
            jira_connection.myself()
    except JIRAError as error:
        detail = None
        if error.text:
            detail = f"JIRAError: {error.text}"
        if error.url:
            detail += f" at url={error.url}"
        raise HTTPException(error.status_code, detail)
    return jira_connection


# FIXME: Remove this function when LDAP integration is fully implemented.
def _connect_to_jira_or_dummy_jira(
    username: str, password: str, config: Config, validate_credentials: bool = False
) -> JIRA | LdapJiraDummy:
    """
    This function is a temporary solution for the quick integration of LDAP. If LDAP is
    configured, an attempt is first made to connect to LDAP. If this fails, a connection
    to JIRA is established. Either a JIRA connection or a JIRA dummy connection is
    returned. The latter simulates a JIRA connection, allowing LDAP to be used without
    requiring changes elsewhere in the code.
    """

    # LDAP is disabled, so connect to JIRA directly
    if config.ldap is None:
        return authenticate_jira_user(
            username, password, config.jira, validate_credentials
        )

    # LDAP is enabled, so try to connect to LDAP first
    try:
        return LdapJiraDummy(authenticate_ldap_user(username, password, config.ldap))
    except HTTPException as error:
        # LDAP connection failed, so try to connect to JIRA if JIRA is enabled
        if config.jira is None:
            raise error
        return authenticate_jira_user(
            username, password, config.jira, validate_credentials
        )
