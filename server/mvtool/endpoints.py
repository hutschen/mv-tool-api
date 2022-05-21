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

from requests import delete
from tornado.web import HTTPError
from .utils.endpoint import SQLAlchemyEndpoint
from .utils.openapi import EndpointOpenAPIMixin
from . import schemas


class DocumentsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.DocumentSchema


class JiraInstancesEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.JiraInstanceSchema
    HIDE_OPERATIONS = ['create', 'update', 'delete']


class JiraProjectsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.JiraProjectSchema
    HIDE_OPERATIONS = ['create', 'update', 'delete']

    async def create(self, object_):
        raise HTTPError(404, 'operation not implemented')

    async def update(self, updated_object, id_):
        raise HTTPError(404, 'operation not implemented')

    async def delete(self, id_):
        raise HTTPError(404, 'operation not implemented')


class JiraIssuesEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.JiraIssueSchema

    async def delete(self, id_):
        raise HTTPError(404, 'operation not implemented')


class TasksEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.TaskSchema


class MeasuresEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.MeasureSchema


class RequirementsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.RequirementSchema


class ProjectsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.ProjectSchema
