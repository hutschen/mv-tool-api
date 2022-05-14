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


class CreateOperationArgsSchema(Schema):
    pass


class GetOperationArgsSchema(Schema):
    id_ = fields.Integer(data_key='id', required=True)


class UpdateOperationArgsSchema(Schema):
    id_ = fields.Integer(data_key='id', required=True)


class DeleteOperationArgsSchema(Schema):
    id_ = fields.Integer(data_key='id', required=True)


class ListOperationArgsSchema(Schema):
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
            self.context.sqlalchemy_session.delete(object_)


class EndpointHandler(RequestHandler):
    def initialize(self, object_schema,
            create_operation_args_schema=CreateOperationArgsSchema,
            get_operation_args_schema=GetOperationArgsSchema,
            update_operation_args_schema=UpdateOperationArgsSchema,
            delete_operation_args_schema=DeleteOperationArgsSchema,
            list_operation_args_schema=ListOperationArgsSchema,
            endpoint_class=Endpoint, **kwargs):

        self._object_schema = object_schema()
        self._objects_schema = object_schema(many=True)
        self._create_operation_args_schema = create_operation_args_schema()
        self._get_operation_args_schema = get_operation_args_schema()
        self._update_operation_args_schema = update_operation_args_schema()
        self._delete_operation_args_schema = delete_operation_args_schema()
        self._list_operation_args_schema = list_operation_args_schema()
        
        context = endpoint_class.CONTEXT_CLASS(self, **kwargs)
        self._endpoint = endpoint_class(context)

    async def prepare(self):
        # collect and decode path and query arguments
        arguments = dict()
        for key, value in (self.path_kwargs | self.request.arguments).items():
            value = value[0] if isinstance(value, list) else value
            arguments[key] = self.decode_argument(value)

        # decode body data
        body = json_decode(self.request.body) if self.request.body else dict()

        validation_error_messages = set()
        if 'GET' == self.request.method:
            # try to get a single object
            try:
                kwargs = self._get_operation_args_schema.load(arguments)
            except ValidationError as error:
                validation_error_messages.update(error.messages)
            else:
                async with self._endpoint.context:
                    object_ = await self._endpoint.get(**kwargs)
                self.finish(self._object_schema.dump(object_))
                return

            # try to get a list of objects
            try:
                kwargs = self._list_operation_args_schema.load(arguments)
            except ValidationError as error:
                validation_error_messages.update(error.messages)
            else:
                async with self._endpoint.context:
                    objects = await self._endpoint.list_(**kwargs)
                self.finish(dict(objects=self._objects_schema.dump(objects)))
                return
            
        elif 'POST' == self.request.method:
            # try to create an object
            try:
                kwargs = self._create_operation_args_schema.load(arguments)
                object_ = self._object_schema.load(body)
            except ValidationError as error:
                validation_error_messages.update(error.messages)
            else:
                async with self._endpoint.context:
                    object_ = await self._endpoint.create(object_, **kwargs)
                self.set_status(201)
                self.finish(self._object_schema.dump(object_))
                return

        elif 'PUT' == self.request.method:
            # try to update an object
            try:
                kwargs = self._update_operation_args_schema.load(arguments)
                object_ = self._object_schema.load(body)
            except ValidationError as error:
                validation_error_messages.update(error.messages)
            else:
                async with self._endpoint.context:
                    object_ = await self._endpoint.update(object_, **kwargs)
                self.finish(self._object_schema.dump(object_))
                return

        elif 'DELETE' == self.request.method:
            # try to delete an object
            try:
                kwargs = self._delete_operation_args_schema.load(arguments)
            except ValidationError as error:
                validation_error_messages.update(error.messages)
            else:
                async with self._endpoint.context:
                    await self._endpoint.delete(**kwargs)
                self.finish()
                return

        raise HTTPError(400, 'Validation of argument or body failed: %s' 
            % str(validation_error_messages))