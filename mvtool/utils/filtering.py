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


from typing import Any
from sqlalchemy.schema import Column


def search_column(column: Column, search_str: str) -> Any:
    """Generate where clause to search for search_str in column"""
    search_str = search_str.replace("%", "\\%").replace("_", "\\_")
    return column.ilike(f"%{search_str}%")


def filter_column_by_values(column: Column, values: list[str | int]) -> Any:
    """Generate where clause to filter column by values"""
    assert len(values) > 0, "str_list must not be empty"
    if len(values) == 1:
        return column == values[0]
    else:
        return column.in_(values)
