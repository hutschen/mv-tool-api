# coding: utf-8
#
# Copyright (C) 2022 Helmar Hutschenreuter
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pytest
from jira import JIRAError, Project
from fastapi import HTTPException
from fastapi.testclient import TestClient
from mvtool import app
from mvtool.auth import get_jira
from mvtool.database import get_session


@pytest.fixture
def client(jira, crud):
    def get_jira_override():
        try:
            yield jira
        except JIRAError as error:
            raise HTTPException(error.status_code, error.text)

    # remove event handlers to avoid side effects
    app.router.on_startup = []
    app.router.on_shutdown = []

    with TestClient(app) as client:
        app.dependency_overrides[get_session] = lambda: crud.session
        app.dependency_overrides[get_jira] = get_jira_override
        yield client


def test_get_user(client, jira, jira_user_data):
    jira.myself.return_value = jira_user_data
    response = client.get("/api/jira-user")
    assert response.status_code == 200
    assert type(response.json()) == dict


def test_list_jira_projects(client, jira, jira_project_data):
    jira.projects.return_value = [jira_project_data]
    response = client.get("/api/jira-projects")
    response_body = response.json()
    assert response.status_code == 200
    assert type(response_body) == list
    assert len(response_body) == 1


def test_get_jira_project(client, jira, jira_project_data):
    jira.project.return_value = jira_project_data
    response = client.get(f"/api/jira-projects/{jira_project_data.id}")
    response_body = response.json()
    assert response.status_code == 200
    assert response_body["id"] == jira_project_data.id


def test_get_jira_issuetypes(client, jira, jira_project_data, jira_issue_type_data):
    jira.project.return_value = jira_project_data
    response = client.get(f"/api/jira-projects/{jira_project_data.id}/jira-issuetypes")
    response_body = response.json()
    assert response.status_code == 200
    assert type(response_body) == list
    assert len(response_body) == 1
    assert response_body[0]["name"] == jira_issue_type_data.name


def test_list_jira_issues(client, jira, jira_project_data, jira_issue_data):
    jira.search_issues.return_value = [jira_issue_data]
    response = client.get(f"/api/jira-projects/{jira_project_data.id}/jira-issues")
    response_body = response.json()
    assert response.status_code == 200
    assert type(response_body) == list
    assert len(response_body) == 1
    assert response_body[0]["project_id"] == jira_project_data.id


def test_get_jira_issue(client, jira, jira_issue_data):
    jira.issue.return_value = jira_issue_data
    response = client.get(f"/api/jira-issues/{jira_issue_data.id}")
    assert response.status_code == 200
    response_body = response.json()
    assert type(response_body) == dict


def test_list_projects(client, jira):
    jira.projects.return_value = []
    response = client.get("/api/projects")
    assert response.status_code == 200
    response_body = response.json()
    assert type(response_body) == list


def test_create_project(client, project_input):
    response = client.post("/api/projects", json=project_input.dict())
    assert response.status_code == 201
    response_body = response.json()
    assert type(response_body) == dict
    assert response_body["name"] == project_input.name


def test_create_project_valid_jira_project_id(client, project_input):
    response = client.post("/api/projects", json=project_input.dict())
    assert response.status_code == 201
    response_body = response.json()
    assert type(response_body) == dict
    assert response_body["name"] == project_input.name


def test_create_project_invalid_jira_project_id(client, jira):
    jira.project.side_effect = JIRAError("error", status_code=404)
    response = client.post(
        "/api/projects",
        json=dict(name="A sample project", jira_project_id="INVALID"),
        auth=("u", "p"),
    )
    assert response.status_code == 404


def test_get_project(client, create_project: Project):
    response = client.get(f"/api/projects/{create_project.id}")
    assert response.status_code == 200
    assert type(response.json()) == dict


def test_update_project(client, create_project: Project):
    orig_name = create_project.name
    updated_name = create_project.name + " (updated)"

    update_response = client.put(
        f"/api/projects/{create_project.id}",
        json=dict(name=updated_name),
        auth=("u", "p"),
    )
    assert update_response.status_code == 200
    updated_project = update_response.json()
    assert updated_project["name"] != orig_name
    assert updated_project["name"] == updated_name


def test_delete_project(client, create_project: Project):
    response = client.delete(f"/api/projects/{create_project.id}")
    assert response.status_code == 204
    response = client.get(f"/api/projects/{create_project.id}")
    assert response.status_code == 404


def test_list_documents(client, create_project: Project):
    response = client.get(f"/api/projects/{create_project.id}/documents")
    assert response.status_code == 200
    assert type(response.json()) == list


def test_create_document(client, create_project: Project):
    response = client.post(
        f"/api/projects/{create_project.id}/documents",
        json=dict(title="A new document"),
        auth=("u", "p"),
    )
    assert response.status_code == 201
    document = response.json()
    assert type(document) == dict


def test_get_document(client, create_document):
    response = client.get(f"/api/documents/{create_document.id}")
    assert response.status_code == 200
    document = response.json()
    assert type(document) == dict


def test_update_document(client, create_document):
    orig_title = create_document.title
    updated_title = orig_title + " (updated)"

    response = client.put(
        f"/api/documents/{create_document.id}",
        json=dict(title=updated_title),
        auth=("u", "p"),
    )
    assert response.status_code == 200
    updated_document = response.json()
    assert updated_document["title"] != orig_title
    assert updated_document["title"] == updated_title


def test_delete_document(client, create_document):
    response = client.delete(f"/api/documents/{create_document.id}")
    assert response.status_code == 204
    response = client.get(f"/api/documents/{create_document.id}")
    assert response.status_code == 404


def test_list_requirements(client, create_project: Project):
    response = client.get(f"/api/projects/{create_project.id}/requirements")
    assert response.status_code == 200
    assert type(response.json()) == list


def test_create_requirement(client, create_project: Project):
    response = client.post(
        f"/api/projects/{create_project.id}/requirements",
        json=dict(summary="A sample requirement"),
        auth=("u", "p"),
    )
    assert response.status_code == 201
    requirement = response.json()
    assert type(requirement) == dict
    assert requirement["project"]["id"] == create_project.id


def test_get_requirement(client, create_requirement):
    response = client.get(f"/api/requirements/{create_requirement.id}")
    assert response.status_code == 200
    assert type(response.json()) == dict


def test_update_requirement(client, create_requirement):
    orig_summary = create_requirement.summary
    updated_summary = create_requirement.summary + " (updated)"

    response = client.put(
        f"/api/requirements/{create_requirement.id}",
        json=dict(summary=updated_summary),
        auth=("u", "p"),
    )
    assert response.status_code == 200
    updated_requirement = response.json()
    assert updated_requirement["summary"] != orig_summary
    assert updated_requirement["summary"] == updated_summary


def test_delete_requirement(client, create_requirement):
    response = client.delete(f"/api/requirements/{create_requirement.id}")
    assert response.status_code == 204
    response = client.get(f"/api/requirements/{create_requirement.id}")
    assert response.status_code == 404


def test_list_measures(client, create_requirement):
    response = client.get(f"/api/requirements/{create_requirement.id}/measures")
    assert response.status_code == 200
    assert type(response.json()) == list


def test_create_measure(client, create_requirement):
    response = client.post(
        f"/api/requirements/{create_requirement.id}/measures",
        json=dict(summary="A sample measure"),
        auth=("u", "p"),
    )
    assert response.status_code == 201
    measure = response.json()
    assert type(measure) == dict
    assert measure["requirement"]["id"] == create_requirement.id


def test_get_measure(client, create_measure):
    response = client.get(f"/api/measures/{create_measure.id}")
    assert response.status_code == 200
    assert type(response.json()) == dict


def test_update_measure(client, create_measure):
    orig_summary = create_measure.summary
    updated_summary = orig_summary + " (updated)"

    response = client.put(
        f"/api/measures/{create_measure.id}",
        json=dict(summary=updated_summary),
        auth=("u", "p"),
    )
    assert response.status_code == 200
    updated_measure = response.json()
    assert updated_measure["summary"] != orig_summary
    assert updated_measure["summary"] == updated_summary


def test_delete_measure(client, create_measure):
    response = client.delete(f"/api/measures/{create_measure.id}")
    assert response.status_code == 204
    response = client.get(f"/api/measures/{create_measure.id}")
    assert response.status_code == 404


def test_create_and_link_jira_issue(client, create_measure, jira_issue_input):
    create_measure.jira_issue_id = None
    response = client.post(
        f"/api/measures/{create_measure.id}/jira-issue",
        json=jira_issue_input.dict(),
        auth=("u", "p"),
    )
    assert response.status_code == 201
    jira_issue = response.json()
    assert type(jira_issue) == dict
    assert jira_issue["summary"] == jira_issue_input.summary


def test_download_measures(client, create_project, create_measure):
    response = client.get(f"/api/projects/{create_project.id}/measures/excel")
    assert response.status_code == 200


def test_download_requirements(client, create_project, create_requirement):
    response = client.get(f"/api/projects/{create_project.id}/requirements/excel")
    assert response.status_code == 200


def test_download_documents(client, create_project, create_document):
    response = client.get(f"/api/projects/{create_project.id}/documents/excel")
    assert response.status_code == 200


def test_upload_requirements(client, create_project):
    with open("tests/data/excel/requirements_valid.xlsx", "rb") as excel_file:
        response = client.post(
            f"/api/projects/{create_project.id}/requirements/excel",
            files=dict(upload_file=excel_file),
        )
    assert response.status_code == 201


def test_upload_requirements_invalid_file(client, create_project):
    with open("tests/data/excel/requirements_invalid_data.xlsx", "rb") as excel_file:
        response = client.post(
            f"/api/projects/{create_project.id}/requirements/excel",
            files=dict(upload_file=excel_file),
        )
    assert response.status_code == 400


def test_upload_requirements_corrupted_file(client, create_project):
    with open("tests/data/corrupted", "rb") as excel_file:
        response = client.post(
            f"/api/projects/{create_project.id}/requirements/excel",
            files=dict(upload_file=excel_file),
        )
    assert response.status_code == 400
    assert len(create_project.requirements) == 0


def test_upload_measures(client, create_requirement):
    with open("tests/data/excel/measures_valid.xlsx", "rb") as excel_file:
        response = client.post(
            f"/api/requirements/{create_requirement.id}/measures/excel",
            files=dict(upload_file=excel_file),
        )
    assert response.status_code == 201


def test_upload_measures_corrupted_file(client, create_requirement):
    with open("tests/data/corrupted", "rb") as excel_file:
        response = client.post(
            f"/api/requirements/{create_requirement.id}/measures/excel",
            files=dict(upload_file=excel_file),
        )
    assert response.status_code == 400


def test_upload_documents(client, create_project):
    with open("tests/data/excel/documents_valid.xlsx", "rb") as excel_file:
        response = client.post(
            f"/api/projects/{create_project.id}/documents/excel",
            files=dict(upload_file=excel_file),
        )
    assert response.status_code == 201


def test_upload_documents_corrupted_file(client, create_project):
    with open("tests/data/corrupted", "rb") as excel_file:
        response = client.post(
            f"/api/projects/{create_project.id}/documents/excel",
            files=dict(upload_file=excel_file),
        )
    assert response.status_code == 400


def test_upload_gs_baustein(client, create_catalog):
    with open("tests/data/gs_bausteine/_valid.docx", "rb") as gs_baustein_file:
        response = client.post(
            f"/api/catalogs/{create_catalog.id}/catalog-modules/gs-baustein",
            files=dict(upload_file=gs_baustein_file),
        )
    assert response.status_code == 201
