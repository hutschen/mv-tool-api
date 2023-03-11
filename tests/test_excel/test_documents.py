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

import io
import mimetypes
from tempfile import NamedTemporaryFile
from unittest.mock import Mock

from fastapi.responses import FileResponse
import pytest

from mvtool.models import Document, DocumentInput, Project
from mvtool.views.excel.documents import (
    DocumentsExcelView,
    convert_document_to_row,
    get_document_excel_headers,
    get_document_excel_headers_only,
)


def test_get_only_document_excel_headers():
    headers = get_document_excel_headers_only()

    header_names = [h.name for h in headers]
    assert header_names == [
        "Document ID",
        "Document Reference",
        "Document Title",
        "Document Description",
    ]


def test_get_document_excel_headers():
    headers = get_document_excel_headers([], [])
    assert len(headers) == 0


def test_convert_document_to_row(create_document: Document):
    row = convert_document_to_row(create_document)

    # check if row contains all expected key/value pairs
    expected = {
        "Document ID": create_document.id,
        "Document Reference": create_document.reference,
        "Document Title": create_document.title,
        "Document Description": create_document.description,
    }
    assert row != expected
    assert all(item in row.items() for item in expected.items())


def test_convert_only_document_to_row(create_document: Document):
    row = convert_document_to_row(create_document, document_only=True)

    assert row == {
        "Document ID": create_document.id,
        "Document Reference": create_document.reference,
        "Document Title": create_document.title,
        "Document Description": create_document.description,
    }


def test_convert_non_existing_document_to_row():
    row = convert_document_to_row(None, document_only=True)

    assert row == {
        "Document ID": None,
        "Document Reference": None,
        "Document Title": None,
        "Document Description": None,
    }


def test_download_document_excel(
    documents_excel_view: DocumentsExcelView,
    excel_temp_file: NamedTemporaryFile,
    create_document: Document,
):
    filename = "test.xlsx"
    response = documents_excel_view.download_documents_excel(
        [], [], temp_file=excel_temp_file, filename=filename
    )

    assert isinstance(response, FileResponse)
    assert response.filename == filename
    assert response.media_type == mimetypes.types_map.get(".xlsx")


def test_bulk_create_update_documents(
    documents_excel_view: DocumentsExcelView,
    create_project: Project,
    create_document: Document,
):
    data = [
        (create_document.id, DocumentInput(title="update")),
        (None, DocumentInput(title="create")),
    ]

    results = list(
        documents_excel_view._bulk_create_update_documents(create_project.id, data)
    )

    assert len(results) == 2
    d1, d2 = results
    assert isinstance(d1, Document)
    assert d1.title == "update"
    assert d1.project.jira_project.id == create_project.jira_project_id

    assert isinstance(d2, Document)
    assert d2.title == "create"
    assert d2.project.jira_project.id == create_project.jira_project_id


@pytest.mark.skip()  # FIXME: fix test after refactoring
def test_upload_documents_excel(
    documents_excel_view: DocumentsExcelView,
    excel_temp_file,
    create_project: Project,
):
    upload_file = Mock()
    upload_file.file = io.FileIO("tests/data/excel/documents_valid.xlsx", "r")

    list(
        documents_excel_view.upload_documents_excel(
            create_project.id, upload_file, excel_temp_file
        )
    )

    assert create_project.documents is not None
    assert len(create_project.documents) > 0
