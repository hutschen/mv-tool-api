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


from pydantic import BaseModel

from ..models import JiraIssue, JiraProject
from .common import Column, ColumnGroup


class JiraProjectImport(BaseModel):
    key: str


def get_jira_project_columns_def() -> ColumnGroup[JiraProjectImport, JiraProject]:
    return ColumnGroup(
        JiraProjectImport,
        "Jira Project",
        [
            Column("Key", "key", required=True),
            Column("Name", "name", Column.EXPORT_ONLY),
            Column("Link", "url", Column.EXPORT_ONLY),
        ],
    )


class JiraIssueImport(BaseModel):
    key: str


def get_jira_issue_columns_def() -> ColumnGroup[JiraIssueImport, JiraIssue]:
    return ColumnGroup(
        JiraIssueImport,
        "Jira Issue",
        [
            Column("Key", "key", required=True),
            Column("Link", "url", Column.EXPORT_ONLY),
        ],
    )
