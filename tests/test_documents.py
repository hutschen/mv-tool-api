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

from fastapi import HTTPException
from jira import Project
import pytest
from mvtool.models import Document, DocumentInput, DocumentOutput
from mvtool.views.documents import DocumentsView


def test_list_document_outputs(
        documents_view: DocumentsView, create_project: Project,
        create_document: Document):
    results = list(documents_view._list_documents(create_project.id))

    assert len(results) == 1
    document_output = results[0]
    assert isinstance(document_output, DocumentOutput)
    assert document_output.id == create_document.id
    assert document_output.project.id == create_project.id

def test_create_document_output(
        documents_view: DocumentsView, create_project: Project, 
        document_input: DocumentInput):
    document_output = documents_view._create_document(
        create_project.id, document_input)

    assert isinstance(document_output, DocumentOutput)
    assert document_output.title == document_input.title
    assert document_output.project.id == create_project.id

def test_create_document_invalid_project_id(
        documents_view: DocumentsView, document_input: DocumentInput):
    with pytest.raises(HTTPException) as excinfo:
        documents_view._create_document('invalid', document_input)
        assert excinfo.value.status_code == 404

def test_get_document_output(
        documents_view: DocumentsView, create_document: Document):
    document_output = documents_view._get_document(create_document.id)

    assert isinstance(document_output, DocumentOutput)
    assert document_output.id == create_document.id
    assert document_output.project.id == create_document.project_id

def test_get_document_output_invalid_id(documents_view: DocumentsView):
    with pytest.raises(HTTPException) as excinfo:
        documents_view._get_document(-1)
        assert excinfo.value.status_code == 404

def test_update_document_output(
        documents_view: DocumentsView, create_document: Document,
        document_input: DocumentInput):
    orig_title = create_document.title
    document_input.title = create_document.title + ' (updated)' 
    document_output = documents_view._update_document(
        create_document.id, document_input)

    assert isinstance(document_output, DocumentOutput)
    assert document_output.title != orig_title
    assert document_output.title == document_input.title
    assert document_output.project.id == create_document.project_id

def test_update_document_output_invalid_id(
        documents_view: DocumentsView, document_input: DocumentInput):
    with pytest.raises(HTTPException) as excinfo:
        documents_view._update_document(-1, document_input)
        assert excinfo.value.status_code == 404

def test_delete_document(
        documents_view: DocumentsView, create_document: Document):
    documents_view.delete_document(create_document.id)
    with pytest.raises(HTTPException) as excinfo:
        documents_view._get_document(create_document.id)
        assert excinfo.value.status_code == 404