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

from email.policy import strict
from tornado.web import RequestHandler
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
    def initialize(self, body_schema,
            create_operation_args_schema=CreateOperationArgsSchema,
            get_operation_args_schema=GetOperationArgsSchema,
            update_operation_args_schema=UpdateOperationArgsSchema,
            delete_operation_args_schema=DeleteOperationArgsSchema,
            list_operation_args_schema=ListOperationArgsSchema):
        self._body_schema = body_schema()
        self._body_list_schema = body_schema(many=True)
        self._create_operation_args_schema = create_operation_args_schema()
        self._get_operation_args_schema = get_operation_args_schema()
        self._update_operation_args_schema = update_operation_args_schema()
        self._delete_operation_args_schema = delete_operation_args_schema()
        self._list_operation_args_schema = list_operation_args_schema()

    def create_object(self, **kwargs):
        raise NotImplementedError

    def get_object(self, **kwargs):
        raise NotImplementedError

    def update_object(self, **kwargs):
        raise NotImplementedError

    def delete_object(self, **kwargs):
        raise NotImplementedError

    def list_objects(self, **kwargs):
        raise NotImplementedError

    def post(self, **kwargs):
        kwargs.update(self.request.arguments)
        create_args = self._create_operation_args_schema.load(kwargs)
        body = self.create_object(**create_args)
        self.set_status(201)
        self.write(self._body_schema.dump(body))

    def get(self, **kwargs):
        kwargs.update(self.request.arguments)
        try:
            get_args = self._get_operation_args_schema.load(kwargs)
        except ValidationError as error:
            pass
        else:
            body = self.get_object(**get_args)
            self.write(self._body_schema.dump(body))

        try:
            list_args = self._list_operation_args_schema.load(kwargs)
        except ValidationError:
            pass
        else:
            objects = self.list_objects(**list_args)
            self.write(self._body_list_schema.dump(objects))

    def put(self, **kwargs):
        kwargs.update(self.request.arguments)
        update_args = self._update_operation_args_schema.load(kwargs)
        body = self.update_object(**update_args)
        self.write(self._body_schema.dump(body))

    def delete(self, **kwargs):
        kwargs.update(self.request.arguments)
        delete_args = self._delete_operation_args_schema.load(kwargs)
        body = self.delete_object(**delete_args)
        self.write(self._body_schema.dump(body))