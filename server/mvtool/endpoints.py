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

from .utils.endpoint import SQLAlchemyEndpoint, SQLAlchemyEndpointContext
from .utils.openapi import EndpointOpenAPIMixin
from .utils.auth import JiraEndpointContext
from . import schemas


class MixedEndpointContext(SQLAlchemyEndpointContext, JiraEndpointContext):
    def __init__(self, handler, sqlalchemy_sessionmaker, **kwargs):
        super(MixedEndpointContext, self).__init__(handler, sqlalchemy_sessionmaker, **kwargs)

    async def __aenter__(self):
        await SQLAlchemyEndpointContext.__aenter__(self)
        await JiraEndpointContext.__aenter__(self)
        return self

    async def __aexit__(self, exception_type, exception_value, traceback):
        await SQLAlchemyEndpointContext.__aexit__(self, exception_type, exception_value, traceback)
        await JiraEndpointContext.__aexit__(self, exception_type, exception_value, traceback)


class DocumentsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.DocumentSchema


class JiraInstancesEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = MixedEndpointContext
    OBJECT_SCHEMA = schemas.JiraInstanceSchema


class JiraProjectsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.JiraProjectSchema


class JiraIssuesEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.JiraIssueSchema


class TasksEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.TaskSchema


class MeasuresEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.MeasureSchema


class RequirementsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.RequirementSchema


class ProjectsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.ProjectSchema
