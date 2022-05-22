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

# Documents
endpoints.DocumentsEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/documents/', operations=dict(
    get=endpoints.DocumentsEndpoint.specify_list(),
    post=endpoints.DocumentsEndpoint.specify_create()
))
openapi_spec.path('/documents/{id}', operations=dict(
    get=endpoints.DocumentsEndpoint.specify_get(),
    put=endpoints.DocumentsEndpoint.specify_update(),
    delete=endpoints.DocumentsEndpoint.specify_delete(),
))

# JIRA instances
endpoints.JiraInstancesEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/jira-instances/', operations=dict(
    get=endpoints.JiraInstancesEndpoint.specify_list(),
))
openapi_spec.path('/jira-instances/{id}', operations=dict(
    get=endpoints.JiraInstancesEndpoint.specify_get(),
))

# JIRA projects
endpoints.JiraProjectsEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/jira-projects/', operations=dict(
    get=endpoints.JiraProjectsEndpoint.specify_list(),
))
openapi_spec.path('/jira-projects/{id}', operations=dict(
    get=endpoints.JiraProjectsEndpoint.specify_get(),
))

# JIRA issues
endpoints.JiraIssuesEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/jira-issues/', operations=dict(
    get=endpoints.JiraIssuesEndpoint.specify_list(),
    post=endpoints.JiraIssuesEndpoint.specify_create()
))
openapi_spec.path('/jira-issues/{id}', operations=dict(
    get=endpoints.JiraIssuesEndpoint.specify_get(),
    put=endpoints.JiraIssuesEndpoint.specify_update(),
))

# Tasks
endpoints.TasksEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/tasks/', operations=dict(
    get=endpoints.TasksEndpoint.specify_list(),
    post=endpoints.TasksEndpoint.specify_create()
))
openapi_spec.path('/tasks/{id}', operations=dict(
    get=endpoints.TasksEndpoint.specify_get(),
    put=endpoints.TasksEndpoint.specify_update(),
    delete=endpoints.TasksEndpoint.specify_delete(),
))

# Measures
endpoints.MeasuresEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/measures/', operations=dict(
    get=endpoints.MeasuresEndpoint.specify_list(),
    post=endpoints.MeasuresEndpoint.specify_create()
))
openapi_spec.path('/measures/{id}', operations=dict(
    get=endpoints.MeasuresEndpoint.specify_get(),
    put=endpoints.MeasuresEndpoint.specify_update(),
    delete=endpoints.MeasuresEndpoint.specify_delete(),
))

# Requirements
endpoints.RequirementsEndpoint.ALLOW_OPERATIONS = set()
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