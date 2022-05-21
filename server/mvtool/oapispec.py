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


import os
import shutil
import json
import jinja2
from apispec import APISpec
from swagger_ui_bundle import swagger_ui_path
from apispec.ext.marshmallow import MarshmallowPlugin
from .endpoints import RequirementsEndpoint


def specify_list_operation(endpoint):
    return dict(
        description='List or filter existing resources.',
        parameters=[ {'in': 'query', 'schema': endpoint.LIST_PARAMS_SCHEMA}],
        responses={200: {
            'description': 'Return the resources.',
            'content': {'application/json': {'schema': endpoint.OBJECT_SCHEMA}}}
        }
    )

def specify_create_operation(endpoint):
    return dict(
        description='Create a new resource.',
        parameters=[{'in': 'query', 'schema': endpoint.CREATE_PARAMS_SCHEMA}],
        requestBody=dict(
            required=True,
            content={'application/json': {'schema': endpoint.OBJECT_SCHEMA}}
        ),
        responses={201: {
            'description': 'Return the resource.',
            'content': {'application/json': {'schema': endpoint.OBJECT_SCHEMA}}}
        }
    )

def specify_get_operation(endpoint):
    return dict(
        description='Get a resource.',
        parameters=[ {'in': 'path', 'schema': endpoint.GET_PARAMS_SCHEMA}],
        responses={200: {
            'description': 'Return the resource.',
            'content': {'application/json': {'schema': endpoint.OBJECT_SCHEMA}}}
        }
    )

def specify_update_operation(endpoint):
    return dict(
        description='Update a resource.',
        parameters=[ {'in': 'path', 'schema': endpoint.UPDATE_PARAMS_SCHEMA}],
        requestBody=dict(
            required=True,
            content={'application/json': {'schema': endpoint.OBJECT_SCHEMA}}
        ),
        responses={200: {
            'description': 'Return the updated resource.',
            'content': {'application/json': {'schema': endpoint.OBJECT_SCHEMA}}}
        }
    )

def specify_delete_operation(endpoint):
    return dict(
        description='Delete a resource.',
        parameters=[{'in': 'path', 'schema': endpoint.DELETE_PARAMS_SCHEMA}],
        responses={200: {'description': 'Resource deleted.'}}
    )


openapi_spec = APISpec(
    title='MV-Tool',
    version='0.0.1',
    openapi_version='3.0.2',
    info=dict(description='API of MV-Tool'),
    plugins=[MarshmallowPlugin()]
)
openapi_spec.path('/requirements/', operations=dict(
    get=specify_list_operation(RequirementsEndpoint),
    post=specify_create_operation(RequirementsEndpoint),
))
openapi_spec.path('/requirements/{id}', operations=dict(
    get=specify_get_operation(RequirementsEndpoint),
    put=specify_update_operation(RequirementsEndpoint),
    delete=specify_delete_operation(RequirementsEndpoint),
))


def prepare_swagger_ui_dir(dirpath, oapi_spec, oapi_filename='openapi.json'):
    index_html_filepath = os.path.join(dirpath, 'index.html')
    oapi_filepath = os.path.join(dirpath, oapi_filename)
    shutil.copytree(swagger_ui_path, dirpath, dirs_exist_ok=True)

    # generate OpenAPI specifiction
    with open(oapi_filepath, 'w', encoding='utf-8') as oapi_fileobj:
        json.dump(oapi_spec.to_dict(), oapi_fileobj, indent=2)

    # generate index.html
    j2_template_loader = jinja2.FileSystemLoader(searchpath=dirpath)
    j2_environment = jinja2.Environment(loader=j2_template_loader)
    j2_environment.get_template('index.j2'
    ).stream(openapi_spec_url=oapi_filename).dump(index_html_filepath)    