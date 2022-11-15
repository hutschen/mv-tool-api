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

from fastapi import HTTPException
import pytest
from mvtool.models import Document, DocumentInput, DocumentOutput, Project
from mvtool.views.documents import DocumentsView


def test_list_document(
    documents_view: DocumentsView, create_project: Project, create_document: Document
):
    results = list(documents_view.list_documents(create_project.id))

    assert len(results) == 1
    document = results[0]
    assert isinstance(document, Document)
    assert document.id == create_document.id
    assert document.project.id == create_project.id
    assert document.project.jira_project.id == create_project.jira_project_id


def test_list_document_with_invalid_project_id(documents_view: DocumentsView):
    result = list(documents_view.list_documents(-1))
    assert len(result) == 0


def test_create_document(
    documents_view: DocumentsView,
    create_project: Project,
    document_input: DocumentInput,
):
    document = documents_view.create_document(create_project.id, document_input)

    assert isinstance(document, Document)
    assert document.title == document_input.title
    assert document.project.id == create_project.id
    assert document.project.jira_project.id == create_project.jira_project_id


def test_create_document_with_invalid_project_id(
    documents_view: DocumentsView, document_input: DocumentInput
):
    with pytest.raises(HTTPException) as excinfo:
        documents_view.create_document(-1, document_input)
    assert excinfo.value.status_code == 404


def test_get_document(documents_view: DocumentsView, create_document: Document):
    document = documents_view.get_document(create_document.id)

    assert isinstance(document, Document)
    assert document.id == create_document.id
    assert document.project.id == create_document.project_id
    assert document.project.jira_project.id == create_document.project.jira_project_id


def test_get_document_with_invalid_id(documents_view: DocumentsView):
    with pytest.raises(HTTPException) as excinfo:
        documents_view.get_document(-1)
    assert excinfo.value.status_code == 404


def test_update_document(
    documents_view: DocumentsView,
    create_project: Project,
    create_document: Document,
    document_input: DocumentInput,
):
    orig_title = create_document.title
    document_input.title = create_document.title + " (updated)"
    document = documents_view.update_document(create_document.id, document_input)

    assert isinstance(document, Document)
    assert document.title != orig_title
    assert document.title == document_input.title
    assert document.project.id == create_document.project_id
    assert document.project.jira_project.id == create_project.jira_project_id


def test_update_document_with_invalid_id(
    documents_view: DocumentsView, document_input: DocumentInput
):
    with pytest.raises(HTTPException) as excinfo:
        documents_view.update_document(-1, document_input)
    assert excinfo.value.status_code == 404


def test_delete_document(documents_view: DocumentsView, create_document: Document):
    documents_view.delete_document(create_document.id)
    with pytest.raises(HTTPException) as excinfo:
        documents_view.get_document(create_document.id)
    assert excinfo.value.status_code == 404
