# coding: utf-8
#
# Copyright (C) 2023 Helmar Hutschenreuter
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
from fastapi import HTTPException
from sqlalchemy.orm import Session

from mvtool.data.documents import Documents
from mvtool.data.projects import Projects
from mvtool.db.schema import Document, Project
from mvtool.handlers.documents import (
    create_document,
    delete_document,
    delete_documents,
    get_document,
    get_document_field_names,
    get_document_references,
    get_document_representations,
    get_documents,
    update_document,
)
from mvtool.models.documents import (
    DocumentInput,
    DocumentOutput,
    DocumentRepresentation,
)
from mvtool.utils.pagination import Page


def test_get_documents_list(documents: Documents):
    documents_list = get_documents([], [], {}, documents)

    assert isinstance(documents_list, list)
    for document in documents_list:
        assert isinstance(document, Document)


def test_get_documents_with_pagination(documents: Documents, document: Document):
    page_params = dict(offset=0, limit=1)
    documents_page = get_documents([], [], page_params, documents)

    assert isinstance(documents_page, Page)
    assert documents_page.total_count >= 1
    for document_ in documents_page.items:
        assert isinstance(document_, DocumentOutput)


def test_create_document(projects: Projects, documents: Documents, project: Project):
    document_input = DocumentInput(title="New Document")
    created_document = create_document(project.id, document_input, projects, documents)

    assert isinstance(created_document, Document)
    assert created_document.title == document_input.title
    assert created_document.project_id == project.id


def test_get_document(documents: Documents, document: Document):
    retrieved_document = get_document(document.id, documents)

    assert isinstance(retrieved_document, Document)
    assert retrieved_document.id == document.id


def test_update_document(documents: Documents, document: Document):
    document_input = DocumentInput(title="Updated Document")
    updated_document = update_document(document.id, document_input, documents)

    assert isinstance(updated_document, Document)
    assert updated_document.id == document.id
    assert updated_document.title == document_input.title


def test_delete_document(documents: Documents, document: Document):
    delete_document(document.id, documents)

    with pytest.raises(HTTPException) as excinfo:
        get_document(document.id, documents)
    assert excinfo.value.status_code == 404
    assert "No Document with id" in excinfo.value.detail


def test_delete_documents(session: Session, documents: Documents):
    # Create documents
    project = Project(name="project")

    for document in [
        Document(title="apple"),
        Document(title="banana"),
        Document(title="cherry"),
    ]:
        session.add(document)
        document.project = project
        session.flush()

    # Delete documents
    delete_documents(
        [Document.title.in_(["apple", "banana"])],
        documents,
    )
    session.flush()

    # Check if documents are deleted
    results = documents.list_documents()
    assert len(results) == 1
    assert results[0].title == "cherry"


def test_get_document_representations_list(documents: Documents, document: Document):
    results = get_document_representations([], None, [], {}, documents)

    assert isinstance(results, list)
    assert len(results) == 1
    for item in results:
        assert isinstance(item, Document)


def test_get_document_representations_with_pagination(
    documents: Documents, document: Document
):
    page_params = dict(offset=0, limit=1)
    resulting_page = get_document_representations([], None, [], page_params, documents)

    assert isinstance(resulting_page, Page)
    assert resulting_page.total_count == 1
    for item in resulting_page.items:
        assert isinstance(item, DocumentRepresentation)


def test_get_document_representations_local_search(
    documents: Documents, project: Project
):
    # Create two documents with different titles
    document_inputs = [
        DocumentInput(reference="apple", title="apple_title", project_id=project.id),
        DocumentInput(reference="banana", title="banana_title", project_id=project.id),
    ]
    for document_input in document_inputs:
        documents.create_document(project, document_input)

    # Get representations using local_search to filter the documents
    local_search = "banana"
    results = get_document_representations([], local_search, [], {}, documents)

    # Check if the correct document is returned after filtering
    assert isinstance(results, list)
    assert len(results) == 1
    document = results[0]
    assert isinstance(document, Document)
    assert document.reference == "banana"
    assert document.title == "banana_title"


def test_get_document_field_names_default_list(documents: Documents):
    field_names = get_document_field_names([], documents)

    assert isinstance(field_names, set)
    assert field_names == {"id", "title", "project"}


def test_get_document_field_names_full_list(documents: Documents, project: Project):
    # Create a document to get all fields
    document_input = DocumentInput(
        title="Example Document",
        reference="Example Reference",
        description="Example description",
    )
    documents.create_document(project, document_input)

    field_names = get_document_field_names([], documents)

    # Check if all field names are returned
    assert isinstance(field_names, set)
    assert field_names == {"id", "title", "project", "reference", "description"}


def test_get_document_references_list(documents: Documents, project: Project):
    # Create a document with a reference
    document_input = DocumentInput(
        reference="ref", title="title", project_id=project.id
    )
    documents.create_document(project, document_input)

    # Get references without pagination
    references = get_document_references([], None, {}, documents)

    # Check if all references are returned
    assert isinstance(references, list)
    assert references == ["ref"]


def test_get_document_references_with_pagination(
    documents: Documents, project: Project
):
    # Create a document with a reference
    document_input = DocumentInput(
        reference="ref", title="title", project_id=project.id
    )
    documents.create_document(project, document_input)

    # Set page_params for pagination
    page_params = dict(offset=0, limit=1)

    # Get references with pagination
    references_page = get_document_references([], None, page_params, documents)

    # Check if the references are returned as a Page instance with the correct reference
    assert isinstance(references_page, Page)
    assert references_page.total_count == 1
    assert references_page.items == ["ref"]


def test_get_document_references_local_search(documents: Documents, project: Project):
    # Create two documents with different references
    document_inputs = [
        DocumentInput(reference="apple", title="apple_title", project_id=project.id),
        DocumentInput(reference="banana", title="banana_title", project_id=project.id),
    ]
    for document_input in document_inputs:
        documents.create_document(project, document_input)

    # Get references using local_search to filter the documents
    local_search = "banana"
    references = get_document_references([], local_search, {}, documents)

    # Check if the correct reference is returned after filtering
    assert isinstance(references, list)
    assert references == ["banana"]
