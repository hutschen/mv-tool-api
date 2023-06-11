# -*- coding: utf-8 -*-
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

from pydantic import BaseModel


class JiraUser(BaseModel):
    display_name: str
    email_address: str


class JiraProjectImport(BaseModel):
    key: str


class JiraProject(JiraProjectImport):
    id: str
    key: str
    name: str
    url: str


class JiraIssueType(BaseModel):
    class Config:
        orm_mode = True

    id: str
    name: str


class JiraIssueStatus(BaseModel):
    name: str
    color_name: str
    completed: bool


class JiraIssueInput(BaseModel):
    summary: str
    description: str | None
    issuetype_id: str


class JiraIssueImport(BaseModel):
    key: str


class JiraIssue(JiraIssueInput):
    id: str
    key: str
    project_id: str
    status: JiraIssueStatus
    url: str
