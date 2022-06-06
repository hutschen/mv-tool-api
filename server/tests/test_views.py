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

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from mvtool import app, on_startup
from mvtool.config import load_config, get_config_filename


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

@pytest.fixture
def credentials():
    config = load_config(get_config_filename())
    return (config.username, config.password)

def test_list_jira_projects(client, credentials):
    response = client.get('/api/jira/projects', auth=credentials)
    response_body = response.json()
    assert response.status_code == 200
    assert type(response_body) == list
    assert 0 < len(response_body), 'Please create at least one project in JIRA.'
    return response_body

@pytest.fixture
def jira_project_id(client, credentials):
    return test_list_jira_projects(client, credentials).pop()['id']

def test_get_jira_project(client, credentials, jira_project_id):
    response = client.get(f'/api/jira/projects/{jira_project_id}', auth=credentials)
    response_body = response.json()
    assert response.status_code == 200
    assert response_body['id'] == jira_project_id
    return response_body

def test_get_jira_issuetypes(client, credentials, jira_project_id):
    response = client.get(
        f'/api/jira/projects/{jira_project_id}/issuetypes', auth=credentials)
    response_body = response.json()
    assert response.status_code == 200
    assert type(response_body) == list
    assert 0 < len([it for it in response_body if it['name'] == 'Task']), \
        'Please create a least the "Task" issue type in your JIRA project.'
    return response_body

def test_list_jira_issues(client, credentials, jira_project_id):
    response = client.get(
        f'/api/jira/projects/{jira_project_id}/issues', auth=credentials)
    response_body = response.json()
    assert response.status_code == 200
    assert type(response_body) == list
    assert 0 < len(response_body),\
        'Please create at least one issue in your JIRA project.'
    return response_body

@pytest.fixture
def jira_issuetype_id(client, credentials, jira_project_id):
    issuetypes = test_get_jira_issuetypes(client, credentials, jira_project_id)
    return [it for it in issuetypes if it['name'] == 'Task'].pop()['id']

def test_create_jira_issue(client, credentials, jira_project_id, jira_issuetype_id):
    response = client.post(
        f'/api/jira/projects/{jira_project_id}/issues', json=dict(
            summary='A test issue',
            issuetype_id=jira_issuetype_id
        ), auth=credentials)
    assert response.status_code == 201

@pytest.fixture
def jira_issue_id(client, credentials, jira_project_id):
    return test_list_jira_issues(client, credentials, jira_project_id).pop()['id']

def test_get_jira_issue(client, credentials, jira_issue_id):
    response = client.get(f'/api/jira/issues/{jira_issue_id}', auth=credentials)
    assert response.status_code == 200
    response_body = response.json()
    assert type(response_body) == dict

def test_list_projects(client, credentials):
    response = client.get('/api/projects', auth=credentials)
    assert response.status_code == 200
    response_body = response.json()
    assert type(response_body) == list
    return response_body

def test_create_project(client, credentials):
    response = client.post('/api/projects', json=dict(
            name='A sample project'), auth=credentials)
    assert response.status_code == 201
    response_body = response.json()
    assert type(response_body) == dict

def test_create_project_valid_jira_project_id(
            client, credentials, jira_project_id):
    response = client.post('/api/projects', json=dict(
            name='A sample project',
            jira_project_id=jira_project_id), auth=credentials)
    assert response.status_code == 201
    return response.json()

def test_create_project_invalid_jira_project_id(client, credentials):
    response = client.post('/api/projects', json=dict(
            name='A sample project',
            jira_project_id='INVALID'), auth=credentials)
    assert response.status_code == 404

@pytest.fixture
def project(client, credentials, jira_project_id):
    return test_create_project_valid_jira_project_id(
        client, credentials, jira_project_id)

@pytest.fixture
def project_id(project):
    return project['id']

def test_get_project(client, credentials, project_id):
    response = client.get(f'/api/projects/{project_id}', auth=credentials)
    assert response.status_code == 200
    assert type(response.json()) == dict

def test_update_project(client, credentials, project):
    orig_project = dict(project)
    project_id = project['id']
    project['name'] = 'An updated project'
    project['jira_project_id'] = None

    response = client.put(
        f'/api/projects/{project_id}', json=project, auth=credentials)
    assert response.status_code == 200
    updated_project = response.json()
    assert updated_project['name'] != orig_project['name']
    assert updated_project['jira_project_id'] == None

def test_delete_project(client, credentials, project_id):
    response = client.delete(f'/api/projects/{project_id}', auth=credentials)
    assert response.status_code == 204

def test_list_requirements(client, credentials, project_id):
    response = client.get(
        f'/api/projects/{project_id}/requirements', auth=credentials)
    assert response.status_code == 200
    assert type(response.json()) == list

@pytest.mark.skip('WIP')
def test_create_requirement(client, credentials, project_id):
    response = client.post(f'/api/projects/{project_id}/requirements', json=dict(
            summary='A sample requirement'), auth=credentials)
    assert response.status_code == 201
    requirement = response.json()
    assert type(requirement) == dict
    assert requirement['project_id'] == project_id