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

from sqlalchemy.future import select
from .utils.endpoint import Endpoint, SQLAlchemyEndpoint, SQLAlchemyEndpointContext
from .utils.openapi import EndpointOpenAPIMixin
from .utils import http_errors, auth
from . import models, schemas


class MixedEndpointContext(SQLAlchemyEndpointContext, auth.JiraEndpointContext):
    def __init__(self, handler, sqlalchemy_sessionmaker, **kwargs):
        super(MixedEndpointContext, self).__init__(handler, sqlalchemy_sessionmaker, **kwargs)

    async def __aenter__(self):
        await SQLAlchemyEndpointContext.__aenter__(self)
        await auth.JiraEndpointContext.__aenter__(self)
        return self

    async def __aexit__(self, exception_type, exception_value, traceback):
        await SQLAlchemyEndpointContext.__aexit__(self, exception_type, exception_value, traceback)
        await auth.JiraEndpointContext.__aexit__(self, exception_type, exception_value, traceback)


class JiraUserEndpoint(Endpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.JiraUserSchema

    def __init__(self, context):
        super().__init__(context)
        self.jira_auth_endpoint = auth.JiraAuthEndpoint(context)
        self.jira_instances_endpoint = JiraInstancesEndpoint(context)

    async def update(self, jira_user):
        # get JIRA user data and authenticate
        jira_credentials = auth.JiraCredentials(
            jira_user.jira_instance.url, jira_user.username, jira_user.password)
        jira_user_data = await jira_credentials.get_jira_myself(jira_credentials)
        await self.jira_auth_endpoint.update(jira_credentials, verify_credentials=False)

        # set display name and email
        print(jira_user_data)

        # get or create JIRA instance
        jira_user.jira_instance = self.jira_instances_endpoint.get_by_url(
            jira_credentials.jira_instance_url, auto_create=True)
        
        return jira_user



class JiraInstancesEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    OBJECT_SCHEMA = schemas.JiraInstanceSchema


    async def get_by_url(self, url, auto_create=False):
        async with self.context.sqlalchemy_session.begin_nested():
            statement = select(self._object_class
                ).where(self._object_class.url == url)
            result = await self.context.sqlalchemy_session.execute(statement)
            jira_instance = result.scalar_one_or_none()
            if jira_instance:
                return jira_instance
            elif auto_create:
                jira_instance = models.JiraInstance(url=url)
                return await self.create(jira_instance)
            else:
                raise http_errors.NotFound(
                    'JiraInstance with url %s not found.' % url)


class JiraProjectsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = MixedEndpointContext
    OBJECT_SCHEMA = schemas.JiraProjectSchema


class JiraIssuesEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = MixedEndpointContext
    OBJECT_SCHEMA = schemas.JiraIssueSchema


class DocumentsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = MixedEndpointContext
    OBJECT_SCHEMA = schemas.DocumentSchema


class TasksEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = MixedEndpointContext
    OBJECT_SCHEMA = schemas.TaskSchema


class MeasuresEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = MixedEndpointContext
    OBJECT_SCHEMA = schemas.MeasureSchema


class RequirementsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = MixedEndpointContext
    OBJECT_SCHEMA = schemas.RequirementSchema


class ProjectsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = MixedEndpointContext
    OBJECT_SCHEMA = schemas.ProjectSchema
