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

from sqlmodel import SQLModel, Field


class JiraProject(SQLModel):
    id: str
    key: str
    name: str


class JiraIssueType(SQLModel):
    id: str
    name: str


class JiraIssueStatus(SQLModel):
    name: str
    color_name: str


class JiraIssueInput(SQLModel):
    summary: str
    description: str | None = None
    issuetype_id: str


class JiraIssue(JiraIssueInput):
    id: str
    key: str
    project_id: str
    status: JiraIssueStatus