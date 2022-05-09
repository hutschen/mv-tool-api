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

import tornado
from tornado.web import RequestHandler, HTTPError
from tornado.escape import json_decode
from marshmallow import Schema, fields
from marshmallow.exceptions import ValidationError


class CreateOperationArgsSchema(Schema):
    id_ = fields.Integer(data_key='id', required=True)


class GetOperationArgsSchema(Schema):
    id_ = fields.Integer(data_key='id', required=True)


class UpdateOperationArgsSchema(Schema):
    id_ = fields.Integer(data_key='id', required=True)


class DeleteOperationArgsSchema(Schema):
    id_ = fields.Integer(data_key='id', required=True)


class ListOperationArgsSchema(Schema):
    page = fields.Integer(missing=1)
    page_size = fields.Integer(missing=None)


class EndpointHandler(RequestHandler):
    def initialize(self, object_schema,
            create_operation_args_schema=CreateOperationArgsSchema,
            get_operation_args_schema=GetOperationArgsSchema,
            update_operation_args_schema=UpdateOperationArgsSchema,
            delete_operation_args_schema=DeleteOperationArgsSchema,
            list_operation_args_schema=ListOperationArgsSchema):
        self._object_schema = object_schema()
        self._objects_schema = object_schema(many=True)
        self._create_operation_args_schema = create_operation_args_schema()
        self._get_operation_args_schema = get_operation_args_schema()
        self._update_operation_args_schema = update_operation_args_schema()
        self._delete_operation_args_schema = delete_operation_args_schema()
        self._list_operation_args_schema = list_operation_args_schema()

    async def list_objects(self, **kwargs):
        raise HTTPError(404, 'Operation not implemented.')

    async def get_object(self, **kwargs):
        raise HTTPError(404, 'Operation not implemented.')

    async def create_object(self, object_, **kwargs):
        raise HTTPError(404, 'Operation not implemented.')

    async def update_object(self, object_, **kwargs):
        raise HTTPError(404, 'Operation not implemented.')

    async def delete_object(self, **kwargs):
        raise HTTPError(404, 'Operation not implemented.')

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
                object_ = await self.get_object(**kwargs)
                self.finish(self._object_schema.dump(object_))
                return

            # try to get a list of objects
            try:
                kwargs = self._list_operation_args_schema.load(arguments)
            except ValidationError as error:
                validation_error_messages.update(error.messages)
            else:
                objects = await self.list_objects(**kwargs)
                self.finish(self._objects_schema.dump(objects))
                return
            
        elif 'POST' == self.request.method:
            # try to create an object
            try:
                kwargs = self._create_operation_args_schema.load(arguments)
                object_ = self._object_schema.load(body)
            except ValidationError as error:
                validation_error_messages.update(error.messages)
            else:
                object_ = await self.create_object(object_, **kwargs)
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
                object_ = await self.update_object(object_, **kwargs)
                self.finish(self._object_schema.dump(object_))
                return

        elif 'DELETE' == self.request.method:
            # try to delete an object
            try:
                kwargs = self._delete_operation_args_schema.load(arguments)
            except ValidationError as error:
                validation_error_messages.update(error.messages)
            else:
                await self.delete_object(object_, **kwargs)
                self.finish()
                return

        raise HTTPError(400, 'Validation of argument or body failed: %s' 
            % str(validation_error_messages))