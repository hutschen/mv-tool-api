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

import json
from urllib import response
import yaml
from tornado.ioloop import IOLoop
from tornado.testing import AsyncHTTPTestCase
from mvtool.utils.auth import JiraCredentialsSchema
from mvtool import App


def load_config(config_filename, config_schema):
    ''' Temporary loading method. Later, the "official" method is to be used, 
        which is also used by the server to load its configuration.
    '''
    with open(config_filename, 'r') as config_file:
        config = yaml.safe_load(config_file)
        return config_schema().load(config)


class TestJiraUser(AsyncHTTPTestCase):
    def get_app(self):
        app = App()
        IOLoop.current().run_sync(app.database.reset)
        return app.tornado_app

    def test_sign_in(self):
        jira_credentials = load_config('tests/config.yml', JiraCredentialsSchema)
        response = self.fetch('/jira-user/', method='PUT', body=json.dumps(dict(
            username=jira_credentials.username,
            password=jira_credentials.password,
            jira_instance=dict(url=jira_credentials.jira_instance_url)
        )))
        self.assertEqual(response.code, 200)

    def test_list_jira_projects(self):
        cookie = {'Cookie': response.headers['Set-Cookie']}
        response = self.fetch('/jira-user/jira-projects/', method='GET', headers=cookie)
        print(response.body)
        self.assertEqual(response.code, 200)

    def test_sign_out(self):
        response = self.fetch('/jira-user/', method='DELETE')
        self.assertEqual(response.code, 200)