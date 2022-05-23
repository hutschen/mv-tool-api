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
from . import endpoints, users


openapi_spec = APISpec(
    title='MV-Tool',
    version='0.0.1',
    openapi_version='3.0.2',
    info=dict(description='API of MV-Tool'),
    plugins=[MarshmallowPlugin()]
)

# Users
users.JiraUserSessionEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/jira-users/', operations=dict(
    put=users.JiraUserSessionEndpoint.specify_update(tags=['jira-users'])
))

# Documents
endpoints.DocumentsEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/documents/', operations=dict(
    get=endpoints.DocumentsEndpoint.specify_list(tags=['documents']),
    post=endpoints.DocumentsEndpoint.specify_create(tags=['documents'])
))
openapi_spec.path('/documents/{id}', operations=dict(
    get=endpoints.DocumentsEndpoint.specify_get(tags=['documents']),
    put=endpoints.DocumentsEndpoint.specify_update(tags=['documents']),
    delete=endpoints.DocumentsEndpoint.specify_delete(tags=['documents']),
))

# JIRA instances
endpoints.JiraInstancesEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/jira-instances/', operations=dict(
    get=endpoints.JiraInstancesEndpoint.specify_list(tags=['jira-instances']),
))
openapi_spec.path('/jira-instances/{id}', operations=dict(
    get=endpoints.JiraInstancesEndpoint.specify_get(tags=['jira-instances']),
))

# JIRA projects
endpoints.JiraProjectsEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/jira-projects/', operations=dict(
    get=endpoints.JiraProjectsEndpoint.specify_list(tags=['jira-projects']),
))
openapi_spec.path('/jira-projects/{id}', operations=dict(
    get=endpoints.JiraProjectsEndpoint.specify_get(tags=['jira-projects']),
))

# JIRA issues
endpoints.JiraIssuesEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/jira-issues/', operations=dict(
    get=endpoints.JiraIssuesEndpoint.specify_list(tags=['jira-issues']),
    post=endpoints.JiraIssuesEndpoint.specify_create(tags=['jira-issues'])
))
openapi_spec.path('/jira-issues/{id}', operations=dict(
    get=endpoints.JiraIssuesEndpoint.specify_get(tags=['jira-issues']),
    put=endpoints.JiraIssuesEndpoint.specify_update(tags=['jira-issues']),
))

# Tasks
endpoints.TasksEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/tasks/', operations=dict(
    get=endpoints.TasksEndpoint.specify_list(tags=['taks']),
    post=endpoints.TasksEndpoint.specify_create(tags=['taks'])
))
openapi_spec.path('/tasks/{id}', operations=dict(
    get=endpoints.TasksEndpoint.specify_get(tags=['taks']),
    put=endpoints.TasksEndpoint.specify_update(tags=['taks']),
    delete=endpoints.TasksEndpoint.specify_delete(tags=['taks']),
))

# Measures
endpoints.MeasuresEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/measures/', operations=dict(
    get=endpoints.MeasuresEndpoint.specify_list(tags=['measures']),
    post=endpoints.MeasuresEndpoint.specify_create(tags=['measures'])
))
openapi_spec.path('/measures/{id}', operations=dict(
    get=endpoints.MeasuresEndpoint.specify_get(tags=['measures']),
    put=endpoints.MeasuresEndpoint.specify_update(tags=['measures']),
    delete=endpoints.MeasuresEndpoint.specify_delete(tags=['measures']),
))

# Requirements
endpoints.RequirementsEndpoint.ALLOW_OPERATIONS = set()
openapi_spec.path('/requirements/', operations=dict(
    # get=specify_list_operation(RequirementsEndpoint),
    get=endpoints.RequirementsEndpoint.specify_list(tags=['requirements']),
    post=endpoints.RequirementsEndpoint.specify_create(tags=['requirements']),
))
openapi_spec.path('/requirements/{id}', operations=dict(
    get=endpoints.RequirementsEndpoint.specify_get(tags=['requirements']),
    put=endpoints.RequirementsEndpoint.specify_update(tags=['requirements']),
    delete=endpoints.RequirementsEndpoint.specify_delete(tags=['requirements']),
))