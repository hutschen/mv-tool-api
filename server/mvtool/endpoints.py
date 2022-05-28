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

from tornado.ioloop import IOLoop
from marshmallow import Schema, fields
from sqlalchemy.future import select
from .utils.endpoint import Endpoint, SQLAlchemyEndpoint, SQLAlchemyEndpointContext, ListParamsSchema
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

    async def get_jira_instance(self):
        return await JiraInstancesEndpoint(self).get_by_url(
            self.jira_credentials.jira_instance_url)


class JiraUserEndpoint(Endpoint, EndpointOpenAPIMixin):
    UPDATE_PARAMS_SCHEMA = Schema.from_dict(dict())
    DELETE_PARAMS_SCHEMA = Schema.from_dict(dict())
    OBJECT_SCHEMA = schemas.JiraUserSchema
    CONTEXT_CLASS = SQLAlchemyEndpointContext

    def __init__(self, context):
        super().__init__(context)
        self.jira_auth_endpoint = auth.JiraAuthEndpoint(context)
        self.jira_instances_endpoint = JiraInstancesEndpoint(context)

    async def update(self, jira_user):
        # get JIRA user data and authenticate
        jira_credentials = auth.JiraCredentials(
            jira_user.jira_instance.url, jira_user.username, jira_user.password)
        jira_user_data = await jira_credentials.get_jira_myself()
        await self.jira_auth_endpoint.update(jira_credentials, verify_credentials=False)

        # set display name and email
        jira_user.display_name = jira_user_data['displayName']
        jira_user.email_address = jira_user_data['emailAddress']

        # get or create JIRA instance
        jira_user.jira_instance = await self.jira_instances_endpoint.get_by_url(
            jira_credentials.jira_instance_url, auto_create=True)
        
        return jira_user

    async def delete(self):
        return await self.jira_auth_endpoint.delete()


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
    LIST_PARAMS_SCHEMA = Schema.from_dict(dict())
    OBJECT_SCHEMA = schemas.JiraProjectSchema

    async def iter_projects_from_jira(self):
        async with self.context.sqlalchemy_session.begin_nested():
            jira_instance = await self.context.get_jira_instance()
            for project in await IOLoop.current().run_in_executor(
                    None, self.context.jira.projects):

                # try to get jira project
                statement = select(self._object_class
                    ).where(self._object_class.key == project.key
                    ).where(self._object_class.jira_instance_id == jira_instance.id)
                result = await self.context.sqlalchemy_session.execute(statement)
                jira_project = result.scalar_one_or_none()
                if jira_project:
                    yield jira_project
                else:
                    yield await self.create(models.JiraProject(
                        key=project.key, name=project.name, 
                        jira_instance=jira_instance))

    async def list_(self):
        return [jp async for jp in self.iter_projects_from_jira()]


class ProjectsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = MixedEndpointContext
    LIST_PARAMS_SCHEMA = Schema.from_dict(dict())
    OBJECT_SCHEMA = schemas.ProjectSchema

    def __init__(self, context):
        super().__init__(context)
        self.jira_projects = JiraProjectsEndpoint(context)

    async def list_(self):
        async with self.context.sqlalchemy_session.begin_nested():
            jira_project_ids = [
                jp.id async for jp in self.jira_projects.iter_projects_from_jira()]
            statement = select(self._object_class).order_by(self._object_class.id
            ).filter(self._object_class.jira_project_id.in_(jira_project_ids))
            result = await self.context.sqlalchemy_session.execute(statement)
            return result.scalars().all()

    async def create(self, project):
        async with self.context.sqlalchemy_session.begin_nested():
            project.jira_project = await self.jira_projects.get(project.jira_project_id)
            return await super().create(project)

    async def update(self, project, id_):
        async with self.context.sqlalchemy_session.begin_nested():
            project.jira_project = await self.jira_projects.get(project.jira_project_id)
            return await super().update(project, id_)


class RequirementsListParamsSchema(ListParamsSchema):
    project_id = fields.Integer(required=True)
    

class RequirementsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = MixedEndpointContext
    LIST_PARAMS_SCHEMA = RequirementsListParamsSchema
    OBJECT_SCHEMA = schemas.RequirementSchema

    def __init__(self, context):
        super().__init__(context)
        self.projects = ProjectsEndpoint(context)

    async def list_(self, page, page_size, project_id):
        statement = select(self._object_class
            ).order_by(self._object_class.id
            ).where(self._object_class.project_id == project_id
            ).limit(page_size
            ).offset((page -1) * page_size)
        result = await self.context.sqlalchemy_session.execute(statement)
        return result.scalars().all()

    async def create(self, requirement):
        async with self.context.sqlalchemy_session.begin_nested():
            requirement.project = await self.projects.get(requirement.project_id)
            return await super().create(requirement)

    async def update(self, requirement, id_):
        async with self.context.sqlalchemy_session.begin_nested():
            requirement.project = await self.projects.get(requirement.project_id)
            return await super().update(requirement, id_)


class MeasuresListParamsSchema(ListParamsSchema):
    requirement_id = fields.Integer(required=True)


class MeasuresEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = MixedEndpointContext
    OBJECT_SCHEMA = schemas.MeasureSchema

    def __init__(self, context):
        super().__init__(context)
        self.requirements = RequirementsEndpoint(context)

    async def list_(self, page, page_size, requirement_id):
        statement = select(self._object_class
            ).order_by(self._object_class.id
            ).where(self._object_class.requirement_id == requirement_id
            ).limit(page_size
            ).offset((page -1) * page_size)
        result = await self.context.sqlalchemy_session.execute(statement)
        return result.scalars().all()

    async def create(self, measure):
        async with self.context.sqlalchemy_session.begin_nested():
            measure.requirement = await self.requirements.get(measure.requirement_id)
            return await super().create(measure)

    async def update(self, measure, id_):
        async with self.context.sqlalchemy_session.begin_nested():
            measure.requirement = await self.projects.get(measure.requirement_id)
            return await super().update(measure, id_)


class JiraIssuesEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = MixedEndpointContext
    OBJECT_SCHEMA = schemas.JiraIssueSchema


class DocumentsEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = MixedEndpointContext
    OBJECT_SCHEMA = schemas.DocumentSchema


class TasksEndpoint(SQLAlchemyEndpoint, EndpointOpenAPIMixin):
    CONTEXT_CLASS = MixedEndpointContext
    OBJECT_SCHEMA = schemas.TaskSchema