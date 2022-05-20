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
from mvtool.schemas import RequirementSchema
from mvtool.utils import endpoint

spec = APISpec(
    title='MV-Tool',
    version='0.0.1',
    openapi_version='3.0.2',
    info=dict(description='API of MV-Tool'),
    plugins=[MarshmallowPlugin()]
)
# spec.components.schema("Requirement", schema=RequirementSchema)
spec.path(
    '/requirements/',
    operations=dict(
        get=dict(
            description='Get requirements.',
            parameters=[ {'in': 'query', 'schema': endpoint.ListArgsSchema}],
            responses={200: {
                'description': 'Return the requirements.',
                'content': {'application/json': {'schema': RequirementSchema}}}
            }
        )
    )
)
spec.path(
    '/requirements/{id}',
    operations=dict(
        get=dict(
            description='Get a requirement.',
            parameters=[ {'in': 'path', 'schema': endpoint.GetArgsSchema}],
            responses={200: {
                'description': 'Return the requirement.',
                'content': {'application/json': {'schema': RequirementSchema}}}
            }
        )
    ),
)

if __name__ == '__main__':
    print(spec.to_yaml())