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

from jira import JIRA
from sqlmodel import Session
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv

from ..auth import get_jira
from ..database import CRUDOperations, get_session
from .projects import ProjectsView
from ..models import DocumentInput, Document, DocumentOutput

router = APIRouter()


@cbv(router)
class DocumentsView(CRUDOperations[Document]):
    kwargs = dict(tags=['document'])

    def __init__(
            self, session: Session = Depends(get_session),
            jira: JIRA = Depends(get_jira)):
        super().__init__(session, Document)
        self.projects = ProjectsView(session, jira)

    @router.get(
        '/projects/{project_id}/documents',
        response_model=list[DocumentOutput], **kwargs)
    def list_documents(self, project_id: int) -> list[Document]:
        return self.read_all_from_db(project_id=project_id)

    @router.post(
        '/projects/{project_id}/documents', status_code=201,
        response_model=DocumentOutput, **kwargs)
    def create_document(
            self, project_id: int, document: DocumentInput) -> Document:
        document = Document.from_orm(document)
        document.project = self.projects.get_project(project_id)
        return self.create_in_db(document)

    @router.get('/documents/{document_id}', response_model=DocumentOutput, **kwargs)
    def get_document(self, document_id: int) -> Document:
        return self.read_from_db(document_id)

    @router.put('/documents/{document_id}', response_model=DocumentOutput, **kwargs)
    def update_document(
            self, document_id: int, document_update: DocumentInput) -> Document:
        document = self.read_from_db(document_id)
        document_update = Document.from_orm(
            document_update, update=dict(project_id=document.project_id))
        return self.update_in_db(document_id, document_update)

    @router.delete('/documents/{document_id}', status_code=204, **kwargs)
    def delete_document(self, document_id: int) -> None:
        return self.delete_in_db(document_id)