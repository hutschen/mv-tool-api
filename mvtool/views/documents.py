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
from fastapi_utils.cbv import cbv
from pydantic import constr
from sqlmodel import Column, func, select, or_
from sqlmodel.sql.expression import Select

from ..utils.pagination import Page, page_params
from ..utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
    search_columns,
)
from ..utils.errors import NotFoundError
from ..database import CRUDOperations, delete_from_db, read_from_db
from .projects import ProjectsView
from ..models.projects import Project
from ..models.documents import (
    DocumentImport,
    DocumentInput,
    Document,
    DocumentOutput,
    DocumentRepresentation,
)

router = APIRouter()


@cbv(router)
class DocumentsView:
    kwargs = dict(tags=["document"])

    def __init__(
        self,
        projects: ProjectsView = Depends(ProjectsView),
        crud: CRUDOperations[Document] = Depends(CRUDOperations),
    ):
        self._projects = projects
        self._crud = crud
        self._session = self._crud.session

    @staticmethod
    def _modify_documents_query(
        query: Select,
        where_clauses: list[Any] | None = None,
        order_by_clauses: list[Any] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Select:
        """Modify a query to include all required joins, clauses and offset and limit."""
        query = query.join(Project)
        if where_clauses:
            query = query.where(*where_clauses)
        if order_by_clauses:
            query = query.order_by(*order_by_clauses)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query

    def list_documents(
        self,
        where_clauses: Any = None,
        order_by_clauses: Any = None,
        offset: int | None = None,
        limit: int | None = None,
        query_jira: bool = True,
    ) -> list[Document]:
        # construct documents query
        query = self._modify_documents_query(
            select(Document),
            where_clauses,
            order_by_clauses or [Document.id],
            offset,
            limit,
        )

        # execute documents query
        documents = self._session.exec(query).all()

        # set jira project on the project related to each document
        if query_jira:
            for document in documents:
                self._set_jira_project(document)

        return documents

    def count_documents(self, where_clauses: Any = None) -> int:
        query = self._modify_documents_query(
            select([func.count()]).select_from(Document), where_clauses
        )
        return self._session.execute(query).scalar()

    def list_document_values(
        self,
        column: Column,
        where_clauses: Any = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        query = self._modify_documents_query(
            select([func.distinct(column)]).select_from(Document),
            [filter_for_existence(column), *where_clauses],
            offset=offset,
            limit=limit,
        )
        return self._session.exec(query).all()

    def count_document_values(self, column: Column, where_clauses: Any = None) -> int:
        query = self._modify_documents_query(
            select([func.count(func.distinct(column))]).select_from(Document),
            [filter_for_existence(column), *where_clauses],
        )
        return self._session.execute(query).scalar()

    def create_document(
        self,
        project: Project,
        creation: DocumentInput | DocumentImport,
        skip_flush: bool = False,
    ) -> Document:
        document = Document(**creation.dict(exclude={"id", "project"}))
        document.project = project

        self._session.add(document)
        if not skip_flush:
            self._session.flush()
        return document

    def get_document(self, document_id: int) -> Document:
        document = read_from_db(self._session, Document, document_id)
        self._set_jira_project(document)
        return document

    def check_document_id(self, document_id: int | None) -> Document | None:
        """Raises an Exception if document ID is not existing or not None."""
        if document_id is not None:
            return self.get_document(document_id)

    def update_document(
        self,
        document: Document,
        update: DocumentInput | DocumentImport,
        patch: bool = False,
        skip_flush: bool = False,
    ) -> Document:
        for key, value in update.dict(
            exclude_unset=patch, exclude={"id", "project"}
        ).items():
            setattr(document, key, value)

        if not skip_flush:
            self._session.flush()

        self._set_jira_project(document)
        return document

    def delete_document(self, document: Document, skip_flush: bool = False) -> None:
        return delete_from_db(self._session, document, skip_flush)

    def _set_jira_project(self, document: Document, try_to_get: bool = True) -> None:
        self._projects._set_jira_project(document.project, try_to_get)


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


@router.get(
    "/documents",
    response_model=Page[DocumentOutput] | list[DocumentOutput],
    **DocumentsView.kwargs,
)
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
    "/projects/{project_id}/documents",
    status_code=201,
    response_model=DocumentOutput,
    **DocumentsView.kwargs,
)
def create_document(
    project_id: int,
    document_input: DocumentInput,
    projects_view: ProjectsView = Depends(),
    documents_view: DocumentsView = Depends(),
) -> Document:
    project = projects_view.get_project(project_id)
    return documents_view.create_document(project, document_input)


@router.get(
    "/documents/{document_id}", response_model=DocumentOutput, **DocumentsView.kwargs
)
def get_document(
    document_id: int, documents_view: DocumentsView = Depends()
) -> Document:
    return documents_view.get_document(document_id)


@router.put(
    "/documents/{document_id}", response_model=DocumentOutput, **DocumentsView.kwargs
)
def update_document(
    document_id: int,
    document_input: DocumentInput,
    documents_view: DocumentsView = Depends(),
) -> Document:
    document = documents_view.get_document(document_id)
    return documents_view.update_document(document, document_input)


@router.delete(
    "/documents/{document_id}",
    status_code=204,
    response_class=Response,
    **DocumentsView.kwargs,
)
def delete_document(
    document_id: int, documents_view: DocumentsView = Depends()
) -> None:
    document = documents_view.get_document(document_id)
    documents_view.delete_document(document)


@router.get(
    "/document/representations",
    response_model=Page[DocumentRepresentation] | list[DocumentRepresentation],
    **DocumentsView.kwargs,
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


@router.get(
    "/document/field-names",
    response_model=list[str],
    **DocumentsView.kwargs,
)
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


@router.get(
    "/document/references",
    response_model=Page[str] | list[str],
    **DocumentsView.kwargs,
)
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
