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


from typing import Any, Iterable, Iterator

from fastapi import Depends
from sqlmodel import Column, Session, func, select
from sqlmodel.sql.expression import Select

from ..database import delete_from_db, get_session, read_from_db
from ..models.documents import Document, DocumentImport, DocumentInput
from ..models.projects import Project
from ..utils.errors import NotFoundError
from ..utils.etag_map import get_from_etag_map
from ..utils.fallback import fallback
from ..utils.filtering import filter_for_existence
from ..utils.iteration import CachedIterable
from .projects import Projects


class Documents:
    def __init__(
        self,
        projects: Projects = Depends(Projects),
        session: Session = Depends(get_session),
    ):
        self._projects = projects
        self._session = session

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
        documents = self._session.execute(query).scalars().all()

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
        where_clauses: list[Any] = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        query = self._modify_documents_query(
            select([func.distinct(column)]).select_from(Document),
            [filter_for_existence(column), *(where_clauses or [])],
            offset=offset,
            limit=limit,
        )
        return self._session.execute(query).scalars().all()

    def count_document_values(
        self, column: Column, where_clauses: list[Any] = None
    ) -> int:
        query = self._modify_documents_query(
            select([func.count(func.distinct(column))]).select_from(Document),
            [filter_for_existence(column), *(where_clauses or [])],
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
    ) -> None:
        for key, value in update.dict(
            exclude_unset=patch, exclude={"id", "project"}
        ).items():
            setattr(document, key, value)

        if not skip_flush:
            self._session.flush()

    def delete_document(self, document: Document, skip_flush: bool = False) -> None:
        return delete_from_db(self._session, document, skip_flush)

    def bulk_create_update_documents(
        self,
        document_imports: Iterable[DocumentImport],
        fallback_project: Project | None = None,
        patch: bool = False,
        skip_flush: bool = False,
    ) -> Iterator[Document]:
        document_imports = CachedIterable(document_imports)

        # Convert project imports to projects
        projects_map = self._projects.convert_project_imports(
            (d.project for d in document_imports if d.project is not None), patch=patch
        )

        # Get documents to be updated from database
        ids = [d.id for d in document_imports if d.id is not None]
        documents_to_update = {
            d.id: d
            for d in (self.list_documents([Document.id.in_(ids)]) if ids else [])
        }

        # Create or update documents
        for document_import in document_imports:
            project = get_from_etag_map(projects_map, document_import.project)

            if document_import.id is None:
                # Create new document
                yield self.create_document(
                    fallback(
                        project, fallback_project, "No fallback project provided."
                    ),
                    document_import,
                    skip_flush=True,
                )
            else:
                # Update existing document
                document = documents_to_update.get(document_import.id)
                if document is None:
                    raise NotFoundError(f"No document with id={document_import.id}.")
                self.update_document(
                    document, document_import, patch=patch, skip_flush=True
                )
                if project is not None:
                    document.project = project
                yield document

        if not skip_flush:
            self._session.flush()

    def convert_document_imports(
        self,
        document_imports: Iterable[DocumentImport],
        fallback_project: Project | None = None,
        patch: bool = False,
    ) -> dict[str, Document]:
        # Map document imports to their etags
        documents_map = {d.etag: d for d in document_imports}

        # Map created and updated documents to the etag of their imports
        for etag, document in zip(
            documents_map.keys(),
            self.bulk_create_update_documents(
                documents_map.values(),
                fallback_project,
                patch=patch,
                skip_flush=True,
            ),
        ):
            documents_map[etag] = document

        return documents_map

    def _set_jira_project(self, document: Document, try_to_get: bool = True) -> None:
        self._projects._set_jira_project(document.project, try_to_get)
