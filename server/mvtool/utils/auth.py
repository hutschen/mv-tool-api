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
from tornado.ioloop import IOLoop
from marshmallow import Schema, fields, post_load
from marshmallow.validate import URL
from jira import JIRA
from jira.exceptions import JIRAError
from .endpoint import Endpoint, EndpointContext
from .openapi import EndpointOpenAPIMixin


class JiraCredentials(object):
    def __init__(self, jira_instance_url, username, password):
        self.jira_instance_url = jira_instance_url
        self.username = username
        self.password = password

    @post_load
    def make_jira_credentials(self, data, **kwargs):
        return JiraCredentials(**data)


class JiraCredentialsSchema(Schema):
    jira_instance_url = fields.Str(validate=URL(schemes=('http', 'https')))
    username = fields.Str()
    password = fields.Str()

    @post_load
    def make_jira_user(self, data, **kwargs):
        return JiraCredentials(**data)


class JiraEndpointContext(EndpointContext):
    def __init__(self, handler):
        super().__init__(handler)
        self.jira = None

    async def __aenter__(self):
        cookie_value = await self._handler.get_secret_cookie('jc')
        if cookie_value is None:
            raise HTTPError(401, 'JIRA authentication cookie was not set')

        jira_credentials = JiraCredentialsSchema().loads(cookie_value)
        self.jira = JIRA(
            jira_credentials.jira_instance_url,
            basic_auth=(jira_credentials.username, jira_credentials.password))
        return self


class JiraAuthEndpoint(Endpoint, EndpointOpenAPIMixin):
    UPDATE_PARAMS_SCHEMA = Schema.from_dict(dict())
    DELETE_PARAMS_SCHEMA = Schema.from_dict(dict())
    OBJECT_SCHEMA = JiraCredentialsSchema

    async def update(self, jira_credentials):
        # verify authentication data
        jira_ = JIRA(
            jira_credentials.jira_instance_url,
            basic_auth=(jira_credentials.username, jira_credentials.password))
        try: 
            await IOLoop.current().run_in_executor(None, jira_.myself)
        except JIRAError as error:
            await self.delete()
            raise HTTPError(401, f'JIRAError: {error.text}')

        # set cookie
        json_str = JiraCredentialsSchema().dumps(jira_credentials)
        await self.context._handler.set_secret_cookie('jc', json_str)

    async def delete(self):
        if await self.context._handler.get_secret_cookie('jc'):
            self.context._handler.clear_cookie('jc')