# coding: utf-8
# 
# Copyright 2022 Helmar Hutschenreuter
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation. You may obtain
# a copy of the GNU AGPL V3 at https://www.gnu.org/licenses/.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AGPL V3 for more details.

from tornado.web import HTTPError
from marshmallow import Schema, fields
from .utils.endpoint import Endpoint, EndpointContext
from .utils.openapi import EndpointOpenAPIMixin


class JiraUser(object):
    def __init__(self, jira_instance_url, username, password):
        self.jira_instance_url = jira_instance_url
        self.username = username
        self.password = password


class JiraUserSchema(Schema):
    class Meta:
        model = JiraUser
        load_instance = True

    jira_instance_url = fields.Str()
    username = fields.Str()
    password = fields.Str()


class JiraUserSessionEndpointContext(EndpointContext):
    def __init__(self, handler, cookie_required=True):
        super().__init__(handler)
        self.jira_user = None
        self._cookie_required = cookie_required

    def _get_jira_user_from_cookie(self):
        json_str = self._handler.get_secure_cookie('ju')
        if not json_str:
            if self._cookie_required:
                raise HTTPError(403, 'can not get jira user data cookie')
            else:
                return
        return JiraUserSchema().loads(json_str)

    def _store_jira_user_in_cookie(self, jira_user):
        json_str = JiraUserSchema().dumps(jira_user)
        self._handler.set_secure_cookie('ju', json_str)

    async def __aenter__(self):
        self.jira_user = self._get_jira_user_from_cookie()
        return self

    async def __aexit__(self, exception_type, exception_value, traceback):
        if self.jira_user:
            self._store_jira_user_in_cookie(self.jira_user)


class JiraUserSessionEndpoint(Endpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = JiraUserSessionEndpointContext
    OBJECT_SCHEMA = JiraUserSchema

    async def create(self, jira_user):
        ''' Authenticate user and create the user session.
        '''
        print(jira_user)
        self.context.jira_user = jira_user
        return jira_user