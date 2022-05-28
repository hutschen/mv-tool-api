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

from unittest import IsolatedAsyncioTestCase

import yaml
from mvtool import SQLAlchemyDatabase, endpoints, schemas, models
from mvtool.utils.auth import JiraCredentialsSchema
from mvtool.utils.endpoint import EndpointContext


def load_config(config_filename, config_schema):
    ''' Temporary loading method. Later, the "official" method is to be used, 
        which is also used by the server to load its configuration.
    '''
    with open(config_filename, 'r') as config_file:
        config = yaml.safe_load(config_file)
        return config_schema().load(config)


class DummyEndpointContext(EndpointContext):
    def __init__(self, database, jira_credentials):
        self.sqlalchemy_session = database.sessionmaker()
        self.jira_credentials = jira_credentials
        self.jira = jira_credentials.jira


class TestJiraUserEndpoint(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.jira_credentials = load_config('tests/config.yml', JiraCredentialsSchema)
        database = SQLAlchemyDatabase('sqlite+aiosqlite:///:memory:')
        context = DummyEndpointContext(database, self.jira_credentials)
        self.endpoint = endpoints.JiraUserEndpoint(context)

    async def test_sign_in(self):
        jira_user = schemas.JiraUserSchema().load(dict(
            username=self.jira_credentials.username,
            password=self.jira_credentials.password,
            jira_instance=dict(url=self.jira_credentials.jira_instance_url)
        ))
        jira_user = await self.endpoint.update(jira_user)
        self.assertIsNotNone(jira_user.display_name)