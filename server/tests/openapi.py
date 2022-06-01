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
from mvtool import MVTool, schemas, models

class BaseTestCase(AsyncHTTPTestCase):
    def setUp(self):
        # do common set up
        self.mvtool = MVTool('tests/config.yml')
        self.mvtool._prepare()
        super().setUp()

        # authenticate and retrieve cookie
        jira_credentials = self.mvtool.config.testing.jira_credentials
        body_data = dict(
            username=jira_credentials.username,
            password=jira_credentials.password,
            jira_instance=dict(url=jira_credentials.jira_instance_url))
        response = self.fetch(
            '/jira-user/', method='PUT', body=json.dumps(body_data))
        self.cookie = response.headers['Set-Cookie']
        
    def tearDown(self):
        super().tearDown()
        self.mvtool._cleanup()

    def get_app(self):
        return self.mvtool.tornado_app


class TestJiraInstances(BaseTestCase):
    def test_list(self):
        response = self.fetch('/jira-instances/', method='GET')
        self.assertEqual(response.code, 200)


class TestJiraProjects(BaseTestCase):
    def test_list(self):
        response = self.fetch(
            '/jira-user/jira-projects/', method='GET', 
            headers={'Cookie': self.cookie})
        self.assertEqual(response.code, 200)

class TestProjects(BaseTestCase):
    def setUp(self):
        super().setUp()

        # get JIRA project as reference for tests
        response = self.fetch(
            '/jira-user/jira-projects/', method='GET',
            headers={'Cookie': self.cookie})
        body_data = json.loads(response.body)
        jira_projects = schemas.JiraProjectSchema(many=True).load(
            body_data['objects'])
        assert 0 < len(jira_projects),\
            'For testing, at least one JIRA project must exist.'
        self.jira_project = jira_projects[0]

    def test_list(self):
        response = self.fetch(
            '/jira-user/projects/', method='GET',
            headers={'Cookie': self.cookie})
        self.assertEqual(response.code, 200)

    def test_create(self):
        project = models.Project(jira_project_id=self.jira_project.id)
        response = self.fetch(
            '/jira-user/projects/', method='POST',
            headers={'Cookie': self.cookie},
            body=schemas.ProjectSchema().dumps(project))
        self.assertEqual(response.code, 201)

    def test_update(self):
        pass

    def test_delete(self):
        pass
