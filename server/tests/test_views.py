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

from urllib import response
from fastapi import Depends
from fastapi.testclient import TestClient
from mvtool import app
from mvtool.config import load_config, get_config_filename

client = TestClient(app)
config = load_config(get_config_filename())
credentials = (config.username, config.password)

def test_list_projects():
    response = client.get('/api/jira/projects', auth=credentials)
    response_body = response.json()
    assert response.status_code == 200
    assert type(response_body) == list
    assert 0 < len(response_body), 'Please create at least one project in JIRA.'
    return response_body

def test_get_project():
    project_id = test_list_projects().pop()['id']
    response = client.get(f'/api/jira/projects/{project_id}', auth=credentials)
    response_body = response.json()
    assert response.status_code == 200
    assert response_body['id'] == project_id
    return response_body

def test_get_issuetypes():
    project_id = test_list_projects().pop()['id']
    response = client.get(
        f'/api/jira/projects/{project_id}/issuetypes', auth=credentials)
    response_body = response.json()
    assert response.status_code == 200
    assert type(response_body) == list
    assert 0 < len([it for it in response_body if it['name'] == 'Task']), \
        'Please create a least the "Task" issue type in your JIRA project.'
    return response_body

def test_create_issue():
    project_id = test_list_projects().pop()['id']
    issuetype_id = [
        it for it in test_get_issuetypes() if it['name'] == 'Task'].pop()['id']
    response = client.post(
        f'/api/jira/projects/{project_id}/issues', json=dict(
            summary='A test issue',
            issuetype_id=issuetype_id
        ), auth=credentials)
    assert response.status_code == 201