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

from tornado.web import RequestHandler, HTTPError
from tornado.escape import json_decode
from sqlalchemy.future import select
from marshmallow import Schema, fields
from marshmallow.validate import Range
from marshmallow.exceptions import ValidationError


class CreateArgsSchema(Schema):
    pass


class GetArgsSchema(Schema):
    id_ = fields.Integer(data_key='id', required=True)


class UpdateArgsSchema(Schema):
    id_ = fields.Integer(data_key='id', required=True)


class DeleteArgsSchema(Schema):
    id_ = fields.Integer(data_key='id', required=True)


class ListArgsSchema(Schema):
    page = fields.Integer(missing=1, validate=Range(min=1))
    page_size = fields.Integer(missing=100, validate=Range(min=1))


class EndpointContext(object):
    def __init__(self, handler):
        self._handler: EndpointHandler = handler
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, exception_type, exception_value, traceback):
        pass


class Endpoint(object):
    CONTEXT_CLASS = EndpointContext
    LIST_ARGS_SCHEMA = ListArgsSchema
    GET_ARGS_SCHEMA = GetArgsSchema
    CREATE_ARGS_SCHEMA = CreateArgsSchema
    UPDATE_ARGS_SCHEMA = UpdateArgsSchema
    DELETE_ARGS_SCHEMA = DeleteArgsSchema
    OBJECT_SCHEMA = None

    def __init__(self, context):
        self.context: EndpointContext = context

    async def __aenter__(self):
        return self

    async def __aexit__(self, exception_type, exception_value, traceback):
        pass
    
    async def list_(self, **kwargs):
        raise HTTPError(404, 'Operation not implemented.')

    async def get(self, **kwargs):
        raise HTTPError(404, 'Operation not implemented.')

    async def create(self, object_, **kwargs):
        raise HTTPError(404, 'Operation not implemented.')

    async def update(self, object_, **kwargs):
        raise HTTPError(404, 'Operation not implemented.')

    async def delete(self, **kwargs):
        raise HTTPError(404, 'Operation not implemented.')


class SQLAlchemyEndpointContext(EndpointContext):
    def __init__(self, handler, sqlalchemy_sessionmaker):
        super().__init__(handler)
        self.sqlalchemy_session = sqlalchemy_sessionmaker()

    async def __aenter__(self):
        self.sqlalchemy_session = \
                await self.sqlalchemy_session.__aenter__()
        return self

    async def __aexit__(self, exception_type, exception_value, traceback):
        await self.sqlalchemy_session.__aexit__(
            exception_type, exception_value, traceback)


class SQLAlchemyEndpoint(Endpoint):
    CONTEXT_CLASS = SQLAlchemyEndpointContext

    def __init__(self, context):
        super().__init__(context)
        self._object_class = self.OBJECT_SCHEMA.Meta.model

    async def list_(self, page, page_size):
        statement = select(self._object_class
            ).order_by(self._object_class.id
            ).limit(page_size
            ).offset((page - 1) * page_size)
        result = await self.context.sqlalchemy_session.execute(statement)
        return result.scalars().all()

    async def get(self, id_):
        statement = select(self._object_class).where(self._object_class.id == id_)
        result = await self.context.sqlalchemy_session.execute(statement)
        object_ = result.scalar_one_or_none()
        if object_:
            return object_
        else:
            raise HTTPError(404, '%s with id %d not found.' % (
            self._object_class.__name__, id_))

    async def create(self, object_):
        object_.id = None
        async with self.context.sqlalchemy_session.begin_nested():
            self.context.sqlalchemy_session.add(object_)
            return object_

    async def update(self, updated_object, id_):
        async with self.context.sqlalchemy_session.begin_nested():
            object_ = await self.get(id_)
            updated_object.id = id_
            return await self.context.sqlalchemy_session.merge(updated_object)

    async def delete(self, id_):
        async with self.context.sqlalchemy_session.begin_nested():
            object_ = await self.get(id_)
            await self.context.sqlalchemy_session.delete(object_)


class EndpointHandler(RequestHandler):
    def initialize(self, endpoint_class=Endpoint, **kwargs):

        context = endpoint_class.CONTEXT_CLASS(self, **kwargs)
        self._endpoint = endpoint_class(context)

    async def prepare(self):
        # collect and decode path and query arguments
        self._arguments = dict()
        for key, value in (self.path_kwargs | self.request.arguments).items():
            value = value[0] if isinstance(value, list) else value
            self._arguments[key] = self.decode_argument(value)

        # decode body data
        self._body = json_decode(self.request.body) if self.request.body else dict()

    async def get(self, **kwargs):
        # try to get a single object
        validation_error_messages = set()
        try:
            kwargs = self._endpoint.GET_ARGS_SCHEMA().load(self._arguments)
        except ValidationError as error:
            validation_error_messages.update(error.messages)
        else:
            async with self._endpoint.context:
                object_ = await self._endpoint.get(**kwargs)
            self.finish(self._endpoint.OBJECT_SCHEMA().dump(object_))
            return

        # try to get a list of objects
        try:
            kwargs = self._endpoint.LIST_ARGS_SCHEMA().load(self._arguments)
        except ValidationError as error:
            validation_error_messages.update(error.messages)
        else:
            async with self._endpoint.context:
                objects = await self._endpoint.list_(**kwargs)
            self.finish(
                dict(objects=self._endpoint.OBJECT_SCHEMA(many=True).dump(objects)))
            return
        
        raise HTTPError(400, 'Validation of arguments failed: %s' 
            % str(validation_error_messages))

    async def post(self, **kwargs):
        # try to create an object
        try:
            kwargs = self._endpoint.CREATE_ARGS_SCHEMA().load(self._arguments)
            object_ = self._endpoint.OBJECT_SCHEMA().load(self._body)
        except ValidationError as error:
            raise HTTPError(
                400, 'Validation of arguments or body failed: %s' % str(error.messages))
        else:
            async with self._endpoint.context:
                object_ = await self._endpoint.create(object_, **kwargs)
            self.set_status(201)
            self.finish(self._endpoint.OBJECT_SCHEMA().dump(object_))
            return

    async def put(self, **kwargs):
        # try to update an object
        try:
            kwargs = self._endpoint.UPDATE_ARGS_SCHEMA().load(self._arguments)
            object_ = self._endpoint.OBJECT_SCHEMA().load(self._body)
        except ValidationError as error:
            raise HTTPError(
                400, 'Validation of arguments or body failed: %s' % str(error.messages))
        else:
            async with self._endpoint.context:
                object_ = await self._endpoint.update(object_, **kwargs)
            self.finish(self._endpoint.OBJECT_SCHEMA().dump(object_))
            return

    async def delete(self, **kwargs):
        # try to delete an object
        try:
            kwargs = self._endpoint.DELETE_ARGS_SCHEMA().load(self._arguments)
        except ValidationError as error:
            raise HTTPError(400, 'Validation of arguments failed: %s' 
                % str(error.messages))
        else:
            async with self._endpoint.context:
                await self._endpoint.delete(**kwargs)
            self.finish()
            return