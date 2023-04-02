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


from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import constr
from sqlmodel import Column, or_

from ..data.documents import DocumentsView
from ..models.documents import (
    Document,
    DocumentInput,
    DocumentOutput,
    DocumentRepresentation,
)
from ..models.projects import Project
from ..utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
    search_columns,
)
from ..utils.pagination import Page, page_params
from .projects import Projects


def get_document_filters(
    # filter by pattern
    reference: str | None = None,
    title: str | None = None,
    description: str | None = None,
    #
    # filter by values
    references: list[str] | None = Query(None),
    #
    # filter by ids
    ids: list[int] | None = Query(None),
    project_ids: list[int] | None = Query(None),
    #
    # filter for existence
    has_reference: bool | None = None,
    has_description: bool | None = None,
    #
    # filter by search string
    search: str | None = None,
) -> list[Any]:
    where_clauses = []

    # filter by pattern
    for column, value in (
        (Document.reference, reference),
        (Document.title, title),
        (Document.description, description),
    ):
        if value:
            where_clauses.append(filter_by_pattern(column, value))

    # filter by values or by ids
    for column, values in (
        (Document.id, ids),
        (Document.reference, references),
        (Document.project_id, project_ids),
    ):
        if values:
            where_clauses.append(filter_by_values(column, values))

    # filter for existence
    for column, value in (
        (Document.reference, has_reference),
        (Document.description, has_description),
    ):
        if value is not None:
            where_clauses.append(filter_for_existence(column, value))

    # filter by search string
    if search:
        where_clauses.append(
            or_(
                filter_by_pattern(column, f"*{search}*")
                for column in (
                    Document.reference,
                    Document.title,
                    Document.description,
                )
            )
        )

    return where_clauses


def get_document_sort(
    sort_by: str | None = None, sort_order: constr(regex=r"^(asc|desc)$") | None = None
) -> list[Any]:
    if not (sort_by and sort_order):
        return []

    try:
        columns: list[Column] = {
            "reference": [Document.reference],
            "title": [Document.title],
            "description": [Document.description],
            "project": [Project.name],
        }[sort_by]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by parameter: {sort_by}",
        )

    columns.append(Document.id)
    if sort_order == "asc":
        return [column.asc() for column in columns]
    else:
        return [column.desc() for column in columns]


router = APIRouter(tags=["document"])


@router.get("/documents", response_model=Page[DocumentOutput] | list[DocumentOutput])
def get_documents(
    where_clauses=Depends(get_document_filters),
    order_by_clauses=Depends(get_document_sort),
    page_params=Depends(page_params),
    documents_view: DocumentsView = Depends(),
):
    documents = documents_view.list_documents(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        documents_count = documents_view.count_documents(where_clauses)
        return Page[DocumentOutput](items=documents, total_count=documents_count)
    else:
        return documents


@router.post(
    "/projects/{project_id}/documents", status_code=201, response_model=DocumentOutput
)
def create_document(
    project_id: int,
    document_input: DocumentInput,
    projects_view: Projects = Depends(),
    documents_view: DocumentsView = Depends(),
) -> Document:
    project = projects_view.get_project(project_id)
    return documents_view.create_document(project, document_input)


@router.get("/documents/{document_id}", response_model=DocumentOutput)
def get_document(
    document_id: int, documents_view: DocumentsView = Depends()
) -> Document:
    return documents_view.get_document(document_id)


@router.put("/documents/{document_id}", response_model=DocumentOutput)
def update_document(
    document_id: int,
    document_input: DocumentInput,
    documents_view: DocumentsView = Depends(),
) -> Document:
    document = documents_view.get_document(document_id)
    documents_view.update_document(document, document_input)
    return document


@router.delete("/documents/{document_id}", status_code=204, response_class=Response)
def delete_document(
    document_id: int, documents_view: DocumentsView = Depends()
) -> None:
    document = documents_view.get_document(document_id)
    documents_view.delete_document(document)


@router.get(
    "/document/representations",
    response_model=Page[DocumentRepresentation] | list[DocumentRepresentation],
)
def get_document_representations(
    where_clauses: list[Any] = Depends(get_document_filters),
    local_search: str | None = None,
    order_by_clauses=Depends(get_document_sort),
    page_params=Depends(page_params),
    documents_view: DocumentsView = Depends(),
):
    if local_search:
        where_clauses.append(
            search_columns(local_search, Document.reference, Document.title)
        )

    documents = documents_view.list_documents(
        where_clauses, order_by_clauses, **page_params, query_jira=False
    )
    if page_params:
        documents_count = documents_view.count_documents(where_clauses)
        return Page[DocumentRepresentation](
            items=documents, total_count=documents_count
        )
    else:
        return documents


@router.get("/document/field-names", response_model=list[str])
def get_document_field_names(
    where_clauses=Depends(get_document_filters),
    document_view: DocumentsView = Depends(),
) -> set[str]:
    field_names = {"id", "title", "project"}
    for field, names in [
        (Document.reference, ["reference"]),
        (Document.description, ["description"]),
    ]:
        if document_view.count_documents(
            [filter_for_existence(field, True), *where_clauses]
        ):
            field_names.update(names)
    return field_names


@router.get("/document/references", response_model=Page[str] | list[str])
def get_document_references(
    where_clauses: list[Any] = Depends(get_document_filters),
    local_search: str | None = None,
    page_params=Depends(page_params),
    document_view: DocumentsView = Depends(),
):
    if local_search:
        where_clauses.append(search_columns(local_search, Document.reference))

    references = document_view.list_document_values(
        Document.reference, where_clauses, **page_params
    )
    if page_params:
        references_count = document_view.count_document_values(
            Document.reference, where_clauses
        )
        return Page[str](items=references, total_count=references_count)
    else:
        return references
