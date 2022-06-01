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
from tornado.testing import AsyncHTTPTestCase
from mvtool import MVTool

class BaseTestCase(AsyncHTTPTestCase):
    def setUp(self):
        self.mvtool = MVTool('tests/config.yml')
        self.mvtool._prepare()
        super().setUp()
        
    def tearDown(self):
        super().tearDown()
        self.mvtool._cleanup()

    def get_app(self):
        return self.mvtool.tornado_app


class TestJiraUser(BaseTestCase):
    def test_sign_in_success(self):
        body_data = dict(
            username=self.mvtool.config.testing.jira_credentials.username,
            password=self.mvtool.config.testing.jira_credentials.password,
            jira_instance=dict(url=self.mvtool.config.testing.jira_credentials.jira_instance_url))
        response = self.fetch(
            '/jira-user/', method='PUT', body=json.dumps(body_data))
        self.assertEqual(response.code, 200)

    def test_sign_in_fail(self):
        body_data = dict(
            username='user',
            password='password',
            jira_instance=dict(url=self.mvtool.config.testing.jira_credentials.jira_instance_url))
        response = self.fetch(
            '/jira-user/', method='PUT', body=json.dumps(body_data))
        self.assertEqual(response.code, 401)

    # def test_list_jira_projects(self):
    #     cookie = {'Cookie': response.headers['Set-Cookie']}
    #     response = self.fetch('/jira-user/jira-projects/', method='GET', headers=cookie)
    #     print(response.body)
    #     self.assertEqual(response.code, 200)

    def test_sign_out(self):
        response = self.fetch('/jira-user/', method='DELETE')
        self.assertEqual(response.code, 200)