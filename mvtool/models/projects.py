# coding: utf-8
#
# Copyright (C) 2023 Helmar Hutschenreuter
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pydantic import field_validator, ConfigDict, BaseModel, confloat

from .common import AbstractProgressCountsOutput, ETagMixin
from .jira_ import JiraProject, JiraProjectImport


class AbstractProjectInput(BaseModel):
    name: str
    description: str | None = None


class ProjectInput(AbstractProjectInput):
    jira_project_id: str | None = None


class ProjectPatch(ProjectInput):
    name: str | None = None

    @field_validator("name")
    def name_validator(cls, v):
        if not v:
            raise ValueError("name must not be empty")
        return v


class ProjectImport(ETagMixin, AbstractProjectInput):
    id: int | None = None
    jira_project: JiraProjectImport | None = None


class ProjectRepresentation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ProjectOutput(AbstractProgressCountsOutput, ProjectInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jira_project: JiraProject | None
