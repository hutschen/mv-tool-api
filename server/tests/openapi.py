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
from tornado.ioloop import IOLoop
from tornado.testing import AsyncHTTPTestCase
from mvtool.config import load_config
from mvtool import App


class TestJiraUser(AsyncHTTPTestCase):
    def get_app(self):
        app = App('tests/config.yml')
        IOLoop.current().run_sync(app.database.reset)
        return app.tornado_app

    def test_sign_in(self):
        config = load_config('tests/config.yml')
        body_data = dict(
            username=config.testing.jira_credentials.username,
            password=config.testing.jira_credentials.password,
            jira_instance=dict(url=config.testing.jira_credentials.jira_instance_url))
        response = self.fetch(
            '/jira-user/', method='PUT', body=json.dumps(body_data))
        self.assertEqual(response.code, 200)

    # def test_list_jira_projects(self):
    #     cookie = {'Cookie': response.headers['Set-Cookie']}
    #     response = self.fetch('/jira-user/jira-projects/', method='GET', headers=cookie)
    #     print(response.body)
    #     self.assertEqual(response.code, 200)

    def test_sign_out(self):
        response = self.fetch('/jira-user/', method='DELETE')
        self.assertEqual(response.code, 200)