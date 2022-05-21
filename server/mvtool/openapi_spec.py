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

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from . import endpoints


openapi_spec = APISpec(
    title='MV-Tool',
    version='0.0.1',
    openapi_version='3.0.2',
    info=dict(description='API of MV-Tool'),
    plugins=[MarshmallowPlugin()]
)
endpoints.JiraInstancesEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/jira-instances/', operations=dict(
    get=endpoints.JiraInstancesEndpoint.specify_list(),
))
openapi_spec.path('/jira-instances/{id}', operations=dict(
    get=endpoints.JiraInstancesEndpoint.specify_get(),
))
openapi_spec.path('/documents/', operations=dict(
    get=endpoints.DocumentsEndpoint.specify_list(),
    post=endpoints.DocumentsEndpoint.specify_create()
))
openapi_spec.path('/documents/{id}', operations=dict(
    get=endpoints.DocumentsEndpoint.specify_get(),
    put=endpoints.DocumentsEndpoint.specify_update(),
    delete=endpoints.DocumentsEndpoint.specify_delete(),
))
openapi_spec.path('/requirements/', operations=dict(
    # get=specify_list_operation(RequirementsEndpoint),
    get=endpoints.RequirementsEndpoint.specify_list(),
    post=endpoints.RequirementsEndpoint.specify_create(),
))
openapi_spec.path('/requirements/{id}', operations=dict(
    get=endpoints.RequirementsEndpoint.specify_get(),
    put=endpoints.RequirementsEndpoint.specify_update(),
    delete=endpoints.RequirementsEndpoint.specify_delete(),
))