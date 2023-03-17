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


from fastapi import Depends, Query

from ..auth import get_jira
from .common import ColumnGroup


def hide_columns(get_columns: callable) -> callable:
    def handler(
        hidden_columns: list[str] | None = Query(None),
        columns: ColumnGroup = Depends(get_columns),
    ) -> ColumnGroup:
        columns.hide_columns(hidden_columns)
        return columns

    return handler


def get_export_labels_handler(get_columns: callable) -> callable:
    def handler(
        columns: ColumnGroup = Depends(get_columns),
        _=Depends(get_jira),  # get jira to enforce login
    ) -> list[str]:
        return columns.export_labels

    return handler
