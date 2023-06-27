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
from sqlalchemy import Column

from ..data.documents import Documents
from ..db.schema import Document, Project
from ..models.documents import (
    DocumentInput,
    DocumentOutput,
    DocumentPatch,
    DocumentRepresentation,
)
from ..utils.filtering import (
    filter_by_pattern_many,
    filter_by_values_many,
    filter_for_existence,
    filter_for_existence_many,
    search_columns,
)
from ..utils.pagination import Page, page_params
from .projects import Projects


def get_document_filters(
    # filter by pattern
    reference: str | None = None,
    title: str | None = None,
    description: str | None = None,
    neg_reference: bool = False,
    neg_title: bool = False,
    neg_description: bool = False,
    #
    # filter by values
    references: list[str] | None = Query(None),
    neg_references: bool = False,
    #
    # filter by ids
    ids: list[int] | None = Query(None),
    project_ids: list[int] | None = Query(None),
    neg_ids: bool = False,
    neg_project_ids: bool = False,
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
    where_clauses.extend(
        filter_by_pattern_many(
            (Document.reference, reference, neg_reference),
            (Document.title, title, neg_title),
            (Document.description, description, neg_description),
        )
    )

    # filter by values or by ids
    where_clauses.extend(
        filter_by_values_many(
            (Document.id, ids, neg_ids),
            (Document.reference, references, neg_references),
            (Document.project_id, project_ids, neg_project_ids),
        )
    )

    # filter for existence
    where_clauses.extend(
        filter_for_existence_many(
            (Document.reference, has_reference),
            (Document.description, has_description),
        )
    )

    # filter by search string
    if search:
        where_clauses.append(
            search_columns(
                search, Document.reference, Document.title, Document.description
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
    documents: Documents = Depends(),
):
    documents_list = documents.list_documents(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        return Page[DocumentOutput](
            items=documents_list,
            total_count=documents.count_documents(where_clauses),
        )
    else:
        return documents_list


@router.post(
    "/projects/{project_id}/documents", status_code=201, response_model=DocumentOutput
)
def create_document(
    project_id: int,
    document_input: DocumentInput,
    projects_view: Projects = Depends(),
    documents_view: Documents = Depends(),
) -> Document:
    return documents_view.create_document(
        projects_view.get_project(project_id),
        document_input,
    )


@router.get("/documents/{document_id}", response_model=DocumentOutput)
def get_document(document_id: int, documents: Documents = Depends()) -> Document:
    return documents.get_document(document_id)


@router.put("/documents/{document_id}", response_model=DocumentOutput)
def update_document(
    document_id: int,
    document_input: DocumentInput,
    documents: Documents = Depends(),
) -> Document:
    document = documents.get_document(document_id)
    documents.update_document(document, document_input)
    return document


@router.patch("/documents/{document_id}", response_model=DocumentOutput)
def patch_document(
    document_id: int,
    document_patch: DocumentPatch,
    documents: Documents = Depends(),
) -> Document:
    document = documents.get_document(document_id)
    documents.patch_document(document, document_patch)
    return document


@router.patch("/documents", response_model=list[DocumentOutput])
def patch_documents(
    patch: DocumentPatch,
    where_clauses: list[Any] = Depends(get_document_filters),
    documents: Documents = Depends(),
) -> list[Document]:
    documents_ = documents.list_documents(where_clauses)
    for document in documents_:
        documents.patch_document(document, patch, skip_flush=True)
    documents._session.flush()
    return documents_


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, documents: Documents = Depends()) -> None:
    document = documents.get_document(document_id)
    documents.delete_document(document)


@router.delete("/documents", status_code=204)
def delete_documents(
    where_clauses: list[Any] = Depends(get_document_filters),
    documents: Documents = Depends(),
) -> None:
    documents_ = documents.list_documents(where_clauses)
    for document in documents_:
        documents.delete_document(document, skip_flush=True)
    documents._session.flush()


@router.get(
    "/document/representations",
    response_model=Page[DocumentRepresentation] | list[DocumentRepresentation],
)
def get_document_representations(
    where_clauses: list[Any] = Depends(get_document_filters),
    local_search: str | None = None,
    order_by_clauses=Depends(get_document_sort),
    page_params=Depends(page_params),
    documents: Documents = Depends(),
):
    if local_search:
        where_clauses.append(
            search_columns(local_search, Document.reference, Document.title)
        )

    documents_list = documents.list_documents(
        where_clauses, order_by_clauses, **page_params, query_jira=False
    )
    if page_params:
        return Page[DocumentRepresentation](
            items=documents_list,
            total_count=documents.count_documents(where_clauses),
        )
    else:
        return documents_list


@router.get("/document/field-names", response_model=list[str])
def get_document_field_names(
    where_clauses=Depends(get_document_filters),
    documents: Documents = Depends(),
) -> set[str]:
    field_names = {"id", "title", "project"}
    for field, names in [
        (Document.reference, ["reference"]),
        (Document.description, ["description"]),
    ]:
        if documents.count_documents(
            [filter_for_existence(field, True), *where_clauses]
        ):
            field_names.update(names)
    return field_names


@router.get("/document/references", response_model=Page[str] | list[str])
def get_document_references(
    where_clauses: list[Any] = Depends(get_document_filters),
    local_search: str | None = None,
    page_params=Depends(page_params),
    documents: Documents = Depends(),
):
    if local_search:
        where_clauses.append(search_columns(local_search, Document.reference))

    references = documents.list_document_values(
        Document.reference, where_clauses, **page_params
    )
    if page_params:
        return Page[str](
            items=references,
            total_count=documents.count_document_values(
                Document.reference, where_clauses
            ),
        )
    else:
        return references
