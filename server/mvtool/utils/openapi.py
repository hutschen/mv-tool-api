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

import os, shutil, json, jinja2
from tempfile import TemporaryDirectory
from swagger_ui_bundle import swagger_ui_path
from marshmallow import Schema, fields


class SwaggerUIDir(TemporaryDirectory):

    @classmethod
    def prepare_swagger_ui_dir(cls, dirpath, oapi_spec, oapi_filename='openapi.json'):
        index_html_filepath = os.path.join(dirpath, 'index.html')
        oapi_filepath = os.path.join(dirpath, oapi_filename)
        shutil.copytree(swagger_ui_path, dirpath, dirs_exist_ok=True)

        # generate OpenAPI specification
        with open(oapi_filepath, 'w', encoding='utf-8') as oapi_fileobj:
            json.dump(oapi_spec.to_dict(), oapi_fileobj, indent=2)

        # generate index.html
        j2_template_loader = jinja2.FileSystemLoader(searchpath=dirpath)
        j2_environment = jinja2.Environment(loader=j2_template_loader)
        j2_environment.get_template('index.j2'
        ).stream(openapi_spec_url=oapi_filename).dump(index_html_filepath)


    def __init__(self, oapi_spec, *args, **kwargs):
        TemporaryDirectory.__init__(self, *args, **kwargs)
        self.prepare_swagger_ui_dir(self.name, oapi_spec)


class EndpointOpenAPIMixin(object):
    @classmethod
    def specify_list(cls, tags=None):
        tags = [] if not tags else list(tags)
        cls.EXPOSE_OPERATIONS.add('list')

        results_schema = Schema.from_dict(
            dict(objects=fields.List(fields.Nested(cls.OBJECT_SCHEMA))),
            name=cls.OBJECT_SCHEMA.__name__.replace('Schema', '') + 'Page'
        )

        return dict(
            summary='List existing resources',
            tags=tags,
            parameters=[ {'in': 'query', 'schema': cls.LIST_PARAMS_SCHEMA}],
            responses={200: {
                'description': 'Return the resources.',
                'content': {'application/json': {'schema': results_schema}}}
            }
        )

    @classmethod
    def specify_create(cls, tags=None):
        tags = [] if not tags else list(tags)
        cls.EXPOSE_OPERATIONS.add('create')

        return dict(
            summary='Create a new resource.',
            tags=tags,
            parameters=[{'in': 'query', 'schema': cls.CREATE_PARAMS_SCHEMA}],
            requestBody=dict(
                required=True,
                content={'application/json': {'schema': cls.OBJECT_SCHEMA}}
            ),
            responses={201: {
                'description': 'Return the resource.',
                'content': {'application/json': {'schema': cls.OBJECT_SCHEMA}}}
            }
        )

    @classmethod
    def specify_get(cls, tags=None):
        tags = [] if not tags else list(tags)
        cls.EXPOSE_OPERATIONS.add('get')

        return dict(
            summary='Get a resource',
            tags=tags,
            parameters=[ {'in': 'path', 'schema': cls.GET_PARAMS_SCHEMA}],
            responses={200: {
                'description': 'Return the resource.',
                'content': {'application/json': {'schema': cls.OBJECT_SCHEMA}}}
            }
        )

    @classmethod
    def specify_update(cls, tags=None):
        tags = [] if not tags else list(tags)
        cls.EXPOSE_OPERATIONS.add('update')

        return dict(
            summary='Update a resource',
            tags=tags,
            parameters=[ {'in': 'path', 'schema': cls.UPDATE_PARAMS_SCHEMA}],
            requestBody=dict(
                required=True,
                content={'application/json': {'schema': cls.OBJECT_SCHEMA}}
            ),
            responses={200: {
                'description': 'Return the updated resource.',
                'content': {'application/json': {'schema': cls.OBJECT_SCHEMA}}}
            }
        )

    @classmethod
    def specify_delete(cls, tags=None):
        tags = [] if not tags else list(tags)
        cls.EXPOSE_OPERATIONS.add('delete')

        return dict(
            summary='Delete a resource',
            tags=tags,
            parameters=[{'in': 'path', 'schema': cls.DELETE_PARAMS_SCHEMA}],
            responses={200: {'description': 'Resource deleted.'}}
        )