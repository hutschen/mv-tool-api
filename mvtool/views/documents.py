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

from typing import Iterator
from fastapi import APIRouter, Depends, Response
from fastapi_utils.cbv import cbv

from ..database import CRUDOperations
from .projects import ProjectsView
from ..models import DocumentInput, Document, DocumentOutput

router = APIRouter()

@cbv(router)
class DocumentsView:
    kwargs = dict(tags=['document'])

    def __init__(self, 
            projects: ProjectsView = Depends(ProjectsView),
            crud: CRUDOperations[Document] = Depends(CRUDOperations)):
        self._projects = projects
        self._crud = crud

    @router.get(
        '/projects/{project_id}/documents',
        response_model=list[DocumentOutput], **kwargs)
    def _list_documents(self, project_id: int) -> Iterator[DocumentOutput]:
        project_output = self._projects._get_project(project_id)
        for document in self.list_documents(project_id):
            yield DocumentOutput.from_orm(
                document, update=dict(project=project_output))

    def list_documents(self, project_id: int) -> list[Document]:
        return self._crud.read_all_from_db(Document, project_id=project_id)

    @router.post(
        '/projects/{project_id}/documents', status_code=201,
        response_model=DocumentOutput, **kwargs)
    def _create_document(
            self, project_id: int, 
            document_input: DocumentInput) -> DocumentOutput:
        return DocumentOutput.from_orm(
            self.create_document(project_id, document_input),
            update=dict(project=self._projects._get_project(project_id)))

    def create_document(
            self, project_id: int, document: DocumentInput) -> Document:
        document = Document.from_orm(document)
        document.project = self._projects.get_project(project_id)
        return self._crud.create_in_db(document)

    @router.get(
        '/documents/{document_id}', response_model=DocumentOutput, **kwargs)
    def _get_document(self, document_id: int) -> DocumentOutput:
        document = self.get_document(document_id)
        return DocumentOutput.from_orm(document, update=dict(
            project=self._projects._get_project(document.project_id)))

    def get_document(self, document_id: int) -> Document:
        return self._crud.read_from_db(Document, document_id)

    def _try_to_get_document(self, document_id: int | None) -> DocumentOutput:
        ''' Returns a DocumentOutput if document_id is not None. '''
        if document_id is not None:
            return self._get_document(document_id)

    def check_document_id(self, document_id: int | None) -> None:
        ''' Raises an Exception if document ID is not existing or not None.
        '''
        if document_id is not None:
            self.get_document(document_id)

    @router.put(
        '/documents/{document_id}', response_model=DocumentOutput, **kwargs)
    def _update_document(
            self, document_id: int, 
            document_input: DocumentInput) -> DocumentOutput:
        document = self.update_document(document_id, document_input)
        return DocumentOutput.from_orm(document, update=dict(
            project=self._projects._get_project(document.project_id)))

    def update_document(
            self, document_id: int, document_update: DocumentInput) -> Document:
        document = self._crud.read_from_db(Document, document_id)
        document_update = Document.from_orm(
            document_update, update=dict(project_id=document.project_id))
        return self._crud.update_in_db(document_id, document_update)

    @router.delete(
        '/documents/{document_id}', status_code=204, response_class=Response, 
        **kwargs)
    def delete_document(self, document_id: int) -> None:
        return self._crud.delete_from_db(Document, document_id)