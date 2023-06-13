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

from unittest.mock import Mock

import pytest
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.sql import select

from mvtool.data.documents import Documents
from mvtool.models.documents import Document, DocumentImport, DocumentInput
from mvtool.models.projects import Project, ProjectImport
from mvtool.utils.errors import NotFoundError, ValueHttpError


def test_modify_documents_query_where_clause(
    session: Session, documents: Documents, project: Project
):
    # Create some test data
    document_inputs = [
        DocumentInput(reference="apple", title="apple_title"),
        DocumentInput(reference="banana", title="banana_title"),
        DocumentInput(reference="cherry", title="cherry_title"),
    ]
    for document_input in document_inputs:
        documents.create_document(project, document_input)

    # Test filtering with a single where clause
    where_clauses = [Document.reference == "banana"]
    query = documents._modify_documents_query(select(Document), where_clauses)
    results: list[Document] = session.execute(query).scalars().all()
    assert len(results) == 1
    assert results[0].reference == "banana"


def test_modify_documents_query_order_by(
    session: Session, documents: Documents, project: Project
):
    # Create some test data
    document_inputs = [
        DocumentInput(reference="apple", title="apple_title"),
        DocumentInput(reference="banana", title="banana_title"),
        DocumentInput(reference="cherry", title="cherry_title"),
    ]
    for document_input in document_inputs:
        documents.create_document(project, document_input)

    # Test ordering
    order_by_clauses = [desc(Document.reference)]
    query = documents._modify_documents_query(
        select(Document), order_by_clauses=order_by_clauses
    )
    results = session.execute(query).scalars().all()
    assert [r.reference for r in results] == ["cherry", "banana", "apple"]


def test_modify_documents_query_offset(
    session: Session, documents: Documents, project: Project
):
    # Create some test data
    document_inputs = [
        DocumentInput(reference="apple", title="apple_title"),
        DocumentInput(reference="banana", title="banana_title"),
        DocumentInput(reference="cherry", title="cherry_title"),
    ]
    for document_input in document_inputs:
        documents.create_document(project, document_input)

    # Test offset
    query = documents._modify_documents_query(select(Document), offset=2)
    results = session.execute(query).scalars().all()
    assert len(results) == 1


def test_modify_documents_query_limit(
    session: Session, documents: Documents, project: Project
):
    # Create some test data
    document_inputs = [
        DocumentInput(reference="apple", title="apple_title"),
        DocumentInput(reference="banana", title="banana_title"),
        DocumentInput(reference="cherry", title="cherry_title"),
    ]
    for document_input in document_inputs:
        documents.create_document(project, document_input)

    # Test limit
    query = documents._modify_documents_query(select(Document), limit=1)
    results = session.execute(query).scalars().all()
    assert len(results) == 1


def test_list_documents(documents: Documents, project: Project):
    # Create some test data
    document_inputs = [
        DocumentInput(reference="apple", title="apple_title"),
        DocumentInput(reference="banana", title="banana_title"),
        DocumentInput(reference="cherry", title="cherry_title"),
    ]
    for document_input in document_inputs:
        documents.create_document(project, document_input)

    # Test listing
    results = documents.list_documents(query_jira=False)
    assert len(results) == len(document_inputs)


def test_list_documents_query_jira(documents: Documents, project: Project):
    # Create some test data
    document_input = DocumentInput(title="title")
    created_document = documents.create_document(project, document_input)

    # Mock _set_jira_project
    documents._set_jira_project = Mock()

    # Test listing
    documents.list_documents(query_jira=True)
    documents._set_jira_project.assert_called_once_with(created_document)


def test_count_documents(documents: Documents, project: Project):
    # Create some test data
    document_inputs = [
        DocumentInput(title="apple_title"),
        DocumentInput(title="banana_title"),
        DocumentInput(title="cherry_title"),
    ]
    for document_input in document_inputs:
        documents.create_document(project, document_input)

    # Test counting documents without any filters
    results = documents.count_documents()
    assert results == len(document_inputs)


def test_list_document_values(documents: Documents, project: Project):
    # Create some test data
    document_inputs = [
        DocumentInput(reference="apple", title="apple_title"),
        DocumentInput(reference="apple", title="banana_title"),
        DocumentInput(reference="cherry", title="cherry_title"),
    ]
    for document_input in document_inputs:
        documents.create_document(project, document_input)

    # Test listing document values without any filters
    results = documents.list_document_values(Document.reference)
    assert len(results) == 2
    assert set(results) == {"apple", "cherry"}


def test_list_document_values_where_clause(documents: Documents, project: Project):
    # Create some test data
    document_inputs = [
        DocumentInput(reference="apple", title="apple_title"),
        DocumentInput(reference="apple", title="banana_title"),
        DocumentInput(reference="cherry", title="cherry_title"),
    ]
    for document_input in document_inputs:
        documents.create_document(project, document_input)

    # Test listing document values with a where clause
    where_clauses = [Document.reference == "apple"]
    results = documents.list_document_values(
        Document.reference, where_clauses=where_clauses
    )
    assert len(results) == 1
    assert results[0] == "apple"


def test_count_document_values(documents: Documents, project: Project):
    # Create some test data
    document_inputs = [
        DocumentInput(reference="apple", title="apple_title"),
        DocumentInput(reference="apple", title="banana_title"),
        DocumentInput(reference="cherry", title="cherry_title"),
    ]
    for document_input in document_inputs:
        documents.create_document(project, document_input)

    # Test counting document values without any filters
    results = documents.count_document_values(Document.reference)
    assert results == 2


def test_count_document_values_where_clause(documents: Documents, project: Project):
    # Create some test data
    document_inputs = [
        DocumentInput(reference="apple", title="apple_title"),
        DocumentInput(reference="apple", title="banana_title"),
        DocumentInput(reference="cherry", title="cherry_title"),
    ]
    for document_input in document_inputs:
        documents.create_document(project, document_input)

    # Test counting document values with a where clause
    where_clauses = [Document.reference == "apple"]
    results = documents.count_document_values(
        Document.reference, where_clauses=where_clauses
    )
    assert results == 1


def test_create_document_from_document_input(documents: Documents, project: Project):
    # Test creating a document from a document input
    document_input = DocumentInput(reference="apple", title="apple_title")
    document = documents.create_document(project, document_input)

    # Check if the document is created with the correct data
    assert document.id is not None
    assert document.reference == document_input.reference
    assert document.title == document_input.title


def test_create_document_from_document_import(documents: Documents, project: Project):
    # Test creating a document from a document import
    document_import = DocumentImport(
        id=-1,  # should be ignored
        reference="apple",
        title="apple_title",
        project=ProjectImport(name="banana_name"),  # should be ignored
    )
    document = documents.create_document(project, document_import)

    # Check if the document is created with the correct data
    assert document.id is not None
    assert document.reference == document_import.reference
    assert document.title == document_import.title

    # Check if ignored fields are not changed
    assert document.id != document_import.id
    assert document.project_id == project.id


def test_create_document_skip_flush(documents: Documents, project: Project):
    document_input = DocumentInput(reference="apple", title="apple_title")
    documents._session = Mock(wraps=documents._session)

    # Test creating a document without flushing the session
    documents.create_document(project, document_input, skip_flush=True)

    # Check if the session is not flushed
    documents._session.flush.assert_not_called()


def test_get_document(documents: Documents, project: Project):
    # Create some test data
    document_input = DocumentInput(reference="apple", title="apple_title")
    document = documents.create_document(project, document_input)

    # Test getting a document
    result = documents.get_document(document.id)

    # Check if the correct document is returned
    assert result.id == document.id


def test_get_document_not_found(documents: Documents):
    # Test getting a document that does not exist
    with pytest.raises(NotFoundError):
        documents.get_document(-1)


def test_check_document_id_succeeds(documents: Documents, project: Project):
    # Create some test data
    document_input = DocumentInput(reference="apple", title="apple_title")
    document = documents.create_document(project, document_input)

    # Test checking an existing document ID
    result = documents.check_document_id(document.id)
    assert result is not None
    assert result.id == document.id


def test_check_document_id_none(documents: Documents):
    # Test checking a None document ID
    result = documents.check_document_id(None)
    assert result is None


def test_check_document_id_fails(documents: Documents):
    # Test checking a non-existing document ID
    with pytest.raises(NotFoundError):
        documents.check_document_id(-1)


def test_update_document_from_document_input(documents: Documents, project: Project):
    # Create some test data
    document_input = DocumentInput(reference="old", title="old_title")
    document = documents.create_document(project, document_input)

    # Test updating a document from a document input
    document_input = DocumentInput(reference="new", title="new_title")
    documents.update_document(document, document_input)

    # Check if the document is updated with the correct data
    assert document.reference == document_input.reference
    assert document.title == document_input.title


def test_update_document_from_document_import(documents: Documents, project: Project):
    # Create some test data
    document_input = DocumentInput(reference="old", title="old_title")
    document = documents.create_document(project, document_input)

    # Test updating a document from a document import
    document_import = DocumentImport(
        id=-1,
        reference="new",
        title="new_title",
        project=ProjectImport(name="new_name"),
    )
    documents.update_document(document, document_import)

    # Check if the document is updated with the correct data
    assert document.reference == document_import.reference
    assert document.title == document_import.title

    # Check if ignored fields are not changed
    assert document.id != document_import.id
    assert document.project_id == project.id


def test_update_document_skip_flush(documents: Documents, project: Project):
    # Create some test data
    document_input = DocumentInput(reference="reference", title="title")
    document = documents.create_document(project, document_input)

    documents._session = Mock(wraps=documents._session)

    # Test updating the document with skip_flush=True
    documents.update_document(document, document_input, skip_flush=True)

    # Check if the flush method was not called
    documents._session.flush.assert_not_called()


def test_update_document_patch(documents: Documents, project: Project):
    # Create some test data
    old_document_input = DocumentInput(reference="old_reference", title="old_title")
    document = documents.create_document(project, old_document_input)

    # Test updating the document with patch=True
    new_document_input = DocumentInput(title="new_title")
    documents.update_document(document, new_document_input, patch=True)

    # Check if the document is updated with the correct data
    assert document.reference == old_document_input.reference
    assert document.title == new_document_input.title


def test_delete_document(documents: Documents, project: Project):
    # Create some test data
    document_input = DocumentInput(title="title")
    document = documents.create_document(project, document_input)

    # Test deleting the document
    documents.delete_document(document)

    # Check if the document is deleted
    with pytest.raises(NotFoundError):
        documents.get_document(document.id)


def test_delete_document_skip_flush(documents: Documents, project: Project):
    # Create some test data
    document_input = DocumentInput(title="title")
    document = documents.create_document(project, document_input)

    documents._session = Mock(wraps=documents._session)

    # Test deleting the document with skip_flush=True
    documents.delete_document(document, skip_flush=True)

    # Check if the flush method was not called
    documents._session.flush.assert_not_called()


def test_bulk_create_update_documents_create(documents: Documents, project: Project):
    # Create some test data
    document_imports = [
        DocumentImport(title="title1"),
        DocumentImport(title="title2"),
    ]

    # Test creating documents and provide a fallback project
    created_documents = list(
        documents.bulk_create_update_documents(document_imports, project)
    )

    # Check if the documents are created with the correct data
    assert len(created_documents) == 2
    for document_import, created_document in zip(document_imports, created_documents):
        assert created_document.id is not None
        assert created_document.title == document_import.title


def test_bulk_create_update_documents_create_without_fallback_project(
    documents: Documents,
):
    # Create some test data
    document_imports = [DocumentImport(title="title")]

    # Test creating documents without providing a fallback project
    with pytest.raises(ValueHttpError):
        list(documents.bulk_create_update_documents(document_imports))


def test_bulk_create_update_documents_create_with_nested_project(
    documents: Documents,
):
    # Create some test data
    document_import = DocumentImport(
        title="title",
        project=ProjectImport(name="name"),
    )

    # Test creating documents with nested projects
    created_documents = list(documents.bulk_create_update_documents([document_import]))

    # Check if the documents are created with the correct data
    assert len(created_documents) == 1
    created_document = created_documents[0]
    assert created_document.id is not None
    assert created_document.title == document_import.title
    assert created_document.project_id is not None
    assert created_document.project.name == document_import.project.name


def test_bulk_create_update_documents_update(documents: Documents, project: Project):
    # Create documents to update
    document_input1 = DocumentInput(title="title1")
    document_input2 = DocumentInput(title="title2")
    created_document1 = documents.create_document(project, document_input1)
    created_document2 = documents.create_document(project, document_input2)

    # Create document imports
    document_imports = [
        DocumentImport(
            id=created_document1.id,
            title="new_title1",
            project=ProjectImport(id=project.id, name=project.name),
        ),
        DocumentImport(
            id=created_document2.id,
            title="new_title2",
        ),
    ]

    # Update documents using document imports
    updated_documents = list(documents.bulk_create_update_documents(document_imports))

    # Check if the documents are updated with the correct data
    assert len(updated_documents) == 2
    for import_, updated in zip(document_imports, updated_documents):
        assert updated.id == import_.id
        assert updated.title == import_.title
        assert updated.project_id == project.id
        assert updated.project.name == project.name


def test_bulk_create_update_documents_not_found_error(
    documents: Documents,
):
    # Create some test data
    document_imports = [DocumentImport(id=-1, title="title")]

    # Test updating documents that do not exist
    with pytest.raises(NotFoundError):
        list(documents.bulk_create_update_documents(document_imports))


def test_bulk_create_update_documents_skip_flush(
    documents: Documents, project: Project
):
    document_imports = [DocumentImport(title="title")]
    documents._session = Mock(wraps=documents._session)

    # Test creating documents with skip_flush=True
    list(
        documents.bulk_create_update_documents(
            document_imports, project, skip_flush=True
        )
    )

    # Check if the flush method was not called
    documents._session.flush.assert_not_called()


def test_convert_document_imports(documents: Documents, project: Project):
    # Create some test data
    document_imports = [
        DocumentImport(title="title1"),
        DocumentImport(title="title2"),
    ]

    # Test converting document imports to documents
    documents_map = documents.convert_document_imports(document_imports, project)

    # Check if the document inputs are created with the correct data
    assert len(documents_map) == 2
    for document_import in document_imports:
        document = documents_map[document_import.etag]
        assert document.title == document_import.title
