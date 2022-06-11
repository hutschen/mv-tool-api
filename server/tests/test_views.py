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
import pytest
from fastapi.testclient import TestClient
from mvtool import app
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
    orig_project = dict(project) # create a copy
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

def test_list_documents(client, credentials, project_id):
    response = client.get(
        f'/api/projects/{project_id}/documents', auth=credentials)
    assert response.status_code == 200
    assert type(response.json()) == list

def test_create_document(client, credentials, project_id):
    response = client.post(
        f'/api/projects/{project_id}/documents', 
        json=dict(title='A new document'), auth=credentials)
    assert response.status_code == 201
    document = response.json()
    assert type(document) == dict
    return document

@pytest.fixture
def document(client, credentials, project_id):
    return test_create_document(client, credentials, project_id)

@pytest.fixture
def document_id(document):
    return document['id']

def test_get_document(client, credentials, document, document_id):
    response = client.get(f'/api/documents/{document_id}', auth=credentials)
    assert response.status_code == 200
    assert response.json() == document

def test_update_document(client, credentials, document, document_id):
    document['title'] = 'An updated document'
    response = client.put(
        f'/api/documents/{document_id}', json=document, auth=credentials)
    assert response.status_code == 200
    assert response.json() == document

def test_delete_document(client, credentials, document_id):
    response = client.delete(f'/api/documents/{document_id}', auth=credentials)
    assert response.status_code == 204
    response = client.get(f'/api/documents/{document_id}', auth=credentials)
    assert response.status_code == 404

def test_list_requirements(client, credentials, project_id):
    response = client.get(
        f'/api/projects/{project_id}/requirements', auth=credentials)
    assert response.status_code == 200
    assert type(response.json()) == list

def test_create_requirement(client, credentials, project_id):
    response = client.post(f'/api/projects/{project_id}/requirements', json=dict(
            summary='A sample requirement'), auth=credentials)
    assert response.status_code == 201
    requirement = response.json()
    assert type(requirement) == dict
    assert requirement['project_id'] == project_id
    return requirement

@pytest.fixture
def requirement(client, credentials, project_id):
    return test_create_requirement(client, credentials, project_id)

@pytest.fixture
def requirement_id(requirement):
    return requirement['id']

def test_get_requirement(client, credentials, requirement_id):
    response = client.get(
        f'/api/requirements/{requirement_id}', auth=credentials)
    assert response.status_code == 200
    assert type(response.json()) == dict

def test_update_requirement(client, credentials, requirement):
    orig_requirement = dict(requirement) # create a copy
    requirement_id = requirement['id']
    requirement['summary'] = 'An updated summary'

    response = client.put(
        f'/api/requirements/{requirement_id}', json=requirement, 
        auth=credentials)
    updated_requirement = response.json()
    assert response.status_code == 200
    assert updated_requirement['summary'] != orig_requirement['summary']
    assert updated_requirement['project_id'] == orig_requirement['project_id']

def test_delete_requirement(client, credentials, requirement_id):
    response = client.delete(
        f'/api/requirements/{requirement_id}', auth=credentials)
    assert response.status_code == 204

def test_list_measures(client, credentials, requirement_id):
    response = client.get(
        f'/api/requirements/{requirement_id}/measures', auth=credentials)
    assert response.status_code == 200
    assert type(response.json()) == list

# @pytest.mark.skip('WIP')
def test_create_measure(client, credentials, requirement_id):
    response = client.post(
        f'/api/requirements/{requirement_id}/measures', 
        json=dict(summary='A test measure'), auth=credentials)
    assert response.status_code == 201
    measure = response.json()
    assert type(measure) == dict
    return measure

@pytest.fixture
def measure(client, credentials, requirement_id):
    return test_create_measure(client, credentials, requirement_id)

@pytest.fixture
def measure_id(measure):
    return measure['id']

def test_get_measure(client, credentials, measure, measure_id):
    response = client.get(f'/api/measures/{measure_id}', auth=credentials)
    assert response.status_code == 200
    assert response.json() == measure

def test_update_measure(client, credentials, measure, measure_id):
    measure['summary'] = 'An updated measure'
    response = client.put(
        f'/api/measures/{measure_id}', json=measure, auth=credentials)
    assert response.status_code == 200
    assert response.json() == measure

def test_delete_measure(client, credentials, measure_id):
    response = client.delete(f'/api/measures/{measure_id}', auth=credentials)
    assert response.status_code == 204
    response = client.get(f'/api/measures/{measure_id}', auth=credentials)
    assert response.status_code == 404