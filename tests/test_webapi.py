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
from jira import JIRAError
from fastapi import Depends, HTTPException
from fastapi.testclient import TestClient
from mvtool import app
from mvtool.auth import http_basic, get_jira
from mvtool.database import CRUDOperations

@pytest.fixture
def client(jira, crud):
    def get_jira_override(credentials = Depends(http_basic)):
        try:
            yield jira
        except JIRAError as error:
            raise HTTPException(error.status_code, error.text)

    # remove event handlers to avoid side effects
    app.router.on_startup = []
    app.router.on_shutdown = []

    with TestClient(app) as client:
        app.dependency_overrides[CRUDOperations] = lambda: crud
        app.dependency_overrides[get_jira] = get_jira_override
        yield client


def test_get_user(client, jira, jira_user_data):
    jira.myself.return_value = jira_user_data
    response = client.get('/api/jira/user', auth=('u', 'p'))
    assert response.status_code == 200
    assert type(response.json()) == dict

def test_list_jira_projects(client, jira, jira_project_data):
    jira.projects.return_value = [jira_project_data]
    response = client.get('/api/jira/projects', auth=('u', 'p'))
    response_body = response.json()
    assert response.status_code == 200
    assert type(response_body) == list
    assert len(response_body) == 1

def test_get_jira_project(client, jira, jira_project_data):
    jira.project.return_value = jira_project_data
    response = client.get(
        f'/api/jira/projects/{jira_project_data.id}', auth=('u', 'p'))
    response_body = response.json()
    assert response.status_code == 200
    assert response_body['id'] == jira_project_data.id

def test_get_jira_issuetypes(
        client, jira, jira_project_data, jira_issue_type_data):
    jira.project.return_value = jira_project_data
    response = client.get(
        f'/api/jira/projects/{jira_project_data.id}/issuetypes',
        auth=('u', 'p'))
    response_body = response.json()
    assert response.status_code == 200
    assert type(response_body) == list
    assert len(response_body) == 1
    assert response_body[0]['name'] == jira_issue_type_data.name

def test_list_jira_issues(client, jira, jira_project_data, jira_issue_data):
    jira.search_issues.return_value = [jira_issue_data]
    response = client.get(
        f'/api/jira/projects/{jira_project_data.id}/issues', auth=('u', 'p'))
    response_body = response.json()
    assert response.status_code == 200
    assert type(response_body) == list
    assert len(response_body) == 1
    assert response_body[0]['project_id'] == jira_project_data.id

def test_create_jira_issue(
        client, jira, jira_project_data, jira_issue_type_data, jira_issue_data):
    jira.create_issue.return_value = jira_issue_data
    response = client.post(
        f'/api/jira/projects/{jira_project_data.id}/issues', json=dict(
            summary=jira_issue_data.fields.summary,
            issuetype_id=jira_issue_type_data.id
        ), auth=('u', 'p'))
    assert response.status_code == 201
    response_body = response.json()
    assert type(response_body) == dict
    assert response_body['id'] == jira_issue_data.id

def test_get_jira_issue(client, jira, jira_issue_data):
    jira.issue.return_value = jira_issue_data
    response = client.get(f'/api/jira/issues/{jira_issue_data.id}', auth=('u', 'p'))
    assert response.status_code == 200
    response_body = response.json()
    assert type(response_body) == dict

def test_list_projects(client, jira):
    jira.projects.return_value = []
    response = client.get('/api/projects', auth=('u', 'p'))
    assert response.status_code == 200
    response_body = response.json()
    assert type(response_body) == list

def test_create_project(client, project):
    response = client.post('/api/projects', json=dict(
            name=project.name), auth=('u', 'p'))
    assert response.status_code == 201
    response_body = response.json()
    assert type(response_body) == dict
    assert response_body['name'] == project.name

def test_create_project_valid_jira_project_id(
            client, jira, jira_project_data, project):
    jira.project.return_value = jira_project_data
    response = client.post('/api/projects', json=dict(
            name=project.name,
            jira_project_id=jira_project_data.id), auth=('u', 'p'))
    assert response.status_code == 201
    response_body = response.json()
    assert type(response_body) == dict
    assert response_body['name'] == project.name
    assert response_body['jira_project']['id'] == jira_project_data.id

def test_create_project_invalid_jira_project_id(client, jira):
    jira.project.side_effect = JIRAError('error', status_code=404)
    response = client.post('/api/projects', json=dict(
            name='A sample project',
            jira_project_id='INVALID'), auth=('u', 'p'))
    assert response.status_code == 404

@pytest.fixture
def create_project_response(client, project_input):
    return client.post(
        '/api/projects', json=project_input.dict(), auth=('u', 'p'))

def test_get_project(client, create_project_response):
    project_data = create_project_response.json()
    project_id = project_data['id']

    response = client.get(
        f'/api/projects/{project_id}', auth=('u', 'p'))
    assert response.status_code == 200
    assert type(response.json()) == dict

def test_update_project(client, create_project_response):
    project_data = create_project_response.json()
    project_id = project_data['id']
    project_name = project_data['name'] + ' (updated)'

    update_response = client.put(
        f'/api/projects/{project_id}', json=dict(
            name=project_name), auth=('u', 'p'))
    assert update_response.status_code == 200
    updated_project = update_response.json()
    assert updated_project['name'] != project_data['name']
    assert updated_project['name'] == project_name

def test_delete_project(client, create_project_response):
    project_data = create_project_response.json()
    project_id = project_data['id']

    response = client.delete(f'/api/projects/{project_id}', auth=('u', 'p'))
    assert response.status_code == 204
    response = client.get(f'/api/projects/{project_id}', auth=('u', 'p'))
    assert response.status_code == 404

def test_list_documents(client, create_project_response):
    project_data = create_project_response.json()
    project_id = project_data['id']

    response = client.get(
        f'/api/projects/{project_id}/documents', auth=('u', 'p'))
    assert response.status_code == 200
    assert type(response.json()) == list

def test_create_document(client, create_project_response):
    project_data = create_project_response.json()
    project_id = project_data['id']

    response = client.post(
        f'/api/projects/{project_id}/documents', 
        json=dict(title='A new document'), auth=('u', 'p'))
    assert response.status_code == 201
    document = response.json()
    assert type(document) == dict

@pytest.fixture
def create_document_response(client, create_project_response, document_input):
    project_data = create_project_response.json()
    project_id = project_data['id']
    return client.post(
        f'/api/projects/{project_id}/documents', 
        json=document_input.dict(), auth=('u', 'p'))

def test_get_document(client, create_document_response):
    document_data = create_document_response.json()
    document_id = document_data['id']

    response = client.get(f'/api/documents/{document_id}', auth=('u', 'p'))
    assert response.status_code == 200
    document = response.json()
    assert type(document) == dict

def test_update_document(client, create_document_response):
    document_data = create_document_response.json()
    document_id = document_data['id']
    document_title = document_data['title'] + ' (updated)'

    response = client.put(
        f'/api/documents/{document_id}', json=dict(
            title=document_title), auth=('u', 'p'))
    assert response.status_code == 200
    updated_document = response.json()
    assert updated_document['title'] != document_data['title']
    assert updated_document['title'] == document_title

def test_delete_document(client, create_document_response):
    document_data = create_document_response.json()
    document_id = document_data['id']

    response = client.delete(f'/api/documents/{document_id}', auth=('u', 'p'))
    assert response.status_code == 204
    response = client.get(f'/api/documents/{document_id}', auth=('u', 'p'))
    assert response.status_code == 404

def test_list_requirements(client, create_project_response):
    project_data = create_project_response.json()
    project_id = project_data['id']

    response = client.get(
        f'/api/projects/{project_id}/requirements', auth=('u', 'p'))
    assert response.status_code == 200
    assert type(response.json()) == list

def test_create_requirement(client, create_project_response):
    project_data = create_project_response.json()
    project_id = project_data['id']

    response = client.post(f'/api/projects/{project_id}/requirements', json=dict(
            summary='A sample requirement'), auth=('u', 'p'))
    assert response.status_code == 201
    requirement = response.json()
    assert type(requirement) == dict
    assert requirement['project']['id'] == project_id

@pytest.fixture
def create_requirement_response(
        client, create_project_response, requirement_input):
    project_data = create_project_response.json()
    project_id = project_data['id']
    return client.post(
        f'/api/projects/{project_id}/requirements', 
        json=requirement_input.dict(), auth=('u', 'p'))

def test_get_requirement(client, create_requirement_response):
    requirement_data = create_requirement_response.json()
    requirement_id = requirement_data['id']

    response = client.get(
        f'/api/requirements/{requirement_id}', auth=('u', 'p'))
    assert response.status_code == 200
    assert type(response.json()) == dict

def test_update_requirement(client, create_requirement_response):
    requirement_data = create_requirement_response.json()
    requirement_id = requirement_data['id']
    requirement_summary = requirement_data['summary'] + ' (updated)'

    response = client.put(
        f'/api/requirements/{requirement_id}', json=dict(
            summary=requirement_summary), auth=('u', 'p'))
    assert response.status_code == 200
    updated_requirement = response.json()
    assert updated_requirement['summary'] != requirement_data['summary']
    assert updated_requirement['summary'] == requirement_summary

def test_delete_requirement(client, create_requirement_response):
    requirement_data = create_requirement_response.json()
    requirement_id = requirement_data['id']

    response = client.delete(
        f'/api/requirements/{requirement_id}', auth=('u', 'p'))
    assert response.status_code == 204
    response = client.get(
        f'/api/requirements/{requirement_id}', auth=('u', 'p'))
    assert response.status_code == 404

def test_list_measures(client, create_requirement_response):
    requirement_data = create_requirement_response.json()
    requirement_id = requirement_data['id']

    response = client.get(
        f'/api/requirements/{requirement_id}/measures', auth=('u', 'p'))
    assert response.status_code == 200
    assert type(response.json()) == list

def test_create_measure(client, create_requirement_response):
    requirement_data = create_requirement_response.json()
    requirement_id = requirement_data['id']

    response = client.post(
        f'/api/requirements/{requirement_id}/measures', 
        json=dict(summary='A sample measure'), auth=('u', 'p'))
    assert response.status_code == 201
    measure = response.json()
    assert type(measure) == dict
    assert measure['requirement']['id'] == requirement_id

@pytest.fixture
def create_measure_response(
        client, create_requirement_response, measure_input):
    requirement_data = create_requirement_response.json()
    requirement_id = requirement_data['id']
    return client.post(
        f'/api/requirements/{requirement_id}/measures', 
        json=measure_input.dict(), auth=('u', 'p'))

def test_get_measure(client, create_measure_response):
    measure_data = create_measure_response.json()
    measure_id = measure_data['id']

    response = client.get(
        f'/api/measures/{measure_id}', auth=('u', 'p'))
    assert response.status_code == 200
    assert type(response.json()) == dict


def test_update_measure(client, create_measure_response):
    measure_data = create_measure_response.json()
    measure_id = measure_data['id']
    measure_summary = measure_data['summary'] + ' (updated)'

    response = client.put(
        f'/api/measures/{measure_id}', json=dict(
            summary=measure_summary), auth=('u', 'p'))
    assert response.status_code == 200
    updated_measure = response.json()
    assert updated_measure['summary'] != measure_data['summary']
    assert updated_measure['summary'] == measure_summary

def test_delete_measure(client, create_measure_response):
    measure_data = create_measure_response.json()
    measure_id = measure_data['id']

    response = client.delete(
        f'/api/measures/{measure_id}', auth=('u', 'p'))
    assert response.status_code == 204
    response = client.get(
        f'/api/measures/{measure_id}', auth=('u', 'p'))
    assert response.status_code == 404