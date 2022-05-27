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

from statistics import mode
from marshmallow import missing, Schema, fields, post_load
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from . import models


class DocumentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = models.Document
        load_instance = True
        transient = True

    project_id = auto_field(required=True)


class JiraInstanceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = models.JiraInstance
        load_instance = True
        transient = True


class JiraUserSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(load_only=True, required=True)
    display_name = fields.Str(dump_only=True)
    email_address = fields.Str(dump_only=True)
    jira_instance = fields.Nested(JiraInstanceSchema, required=True)

    @post_load
    def make_jira_user(self, data, **kwargs):
        return models.JiraUser(**data)


class JiraProjectSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = models.JiraProject
        load_instance = True
        transient = True

    jira_instance_id = auto_field(required=True)


class JiraIssueSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = models.JiraIssue
        load_instance = True
        transient = True

    jira_project_id = auto_field(required=True)


class TaskSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = models.Task
        load_instance = True
        transient = True

    jira_issue_id = auto_field(missing=None)
    measure_id = auto_field(required=True)
    document_id = auto_field(missing=None)


class MeasureSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = models.Measure
        load_instance = True
        transient = True

    requirement_id = auto_field(required=True)


class RequirementSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = models.Requirement
        load_instance = True
        transient = True

    project_id = auto_field(required=True)


class ProjectSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = models.Project
        load_instance = True
        transient = True

    jira_project_id = auto_field(required=True)