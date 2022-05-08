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

from tornado.web import RequestHandler
from marshmallow import Schema, fields


class CreateOperationArgsSchema(Schema):
    id_ = fields.Integer(data_key='id')

class GetOperationArgsSchema(Schema):
    id_ = fields.Integer(data_key='id')

class UpdateOperationArgsSchema(Schema):
    id_ = fields.Integer(data_key='id')

class DeleteOperationArgsSchema(Schema):
    id_ = fields.Integer(data_key='id')

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
        self._body_schema = body_schema
        self._create_operation_args_schema = create_operation_args_schema
        self._get_operation_args_schema = get_operation_args_schema
        self._update_operation_args_schema = update_operation_args_schema
        self._delete_operation_args_schema = delete_operation_args_schema
        self._list_operation_args_schema = list_operation_args_schema

    def create_object(self, args):
        raise NotImplementedError()

    def get_object(self, args):
        raise NotImplementedError()

    def update_object(self, args):
        raise NotImplementedError()

    def delete_object(self, args):
        raise NotImplementedError()

    def list_objects(self, args):
        raise NotImplementedError()

    def post(self, **kwargs):
        pass

    def get(self, **kwargs):
        pass

    def put(self, **kwargs):
        pass

    def delete(self, **kwargs):
        pass