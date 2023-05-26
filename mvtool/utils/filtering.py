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
from sqlmodel import Column, AutoString, and_, or_


def filter_by_pattern(column: Column, pattern: str, negate: bool = False) -> Any:
    """Generate where clause to filter column by string that may contain * and ?"""
    assert isinstance(column.type, AutoString), "column must be of type string"

    #  change commonly used wildcards * and ? to SQL wildcards % and _
    pattern = (
        pattern.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .replace("?", "_")
        .replace("*", "%")
    )

    return ~column.ilike(pattern) if negate else column.ilike(pattern)


def filter_by_pattern_many(
    *args: tuple[Column, str | None] | tuple[Column, str | None, bool]
):
    for column, pattern, *more in args:
        if pattern:
            yield filter_by_pattern(column, pattern, *more)


def filter_by_values(column: Column, values: list[str | int]) -> Any:
    """Generate where clause to filter column by values"""
    assert len(values) > 0, "str_list must not be empty"
    if len(values) == 1:
        return column == values[0]
    else:
        return column.in_(values)


def filter_by_values_many(*args: tuple[Column, list[str] | list[int] | None]):
    for column, values in args:
        if values:
            yield filter_by_values(column, values)


def filter_for_existence(column: Column, exists: bool = True) -> Any:
    """Generate where clause to filter column for existence"""
    none_clause = column.isnot(None) if exists else column.is_(None)
    if isinstance(column.type, AutoString):
        # also check for empty string if column is of type string
        str_clause = column != "" if exists else column == ""
        return (and_ if exists else or_)(none_clause, str_clause)
    else:
        return none_clause


def filter_for_existence_many(*args: tuple[Column, bool | None]):
    for column, exists in args:
        if exists is not None:
            yield filter_for_existence(column, exists)


def search_columns(search_str: str, columns_head: Column, *columns_tail: Column) -> Any:
    """Generate where clause to search for search string in columns"""
    search_str = f"*{search_str}*"
    if columns_tail:
        return or_(
            filter_by_pattern(c, search_str) for c in (columns_head, *columns_tail)
        )
    else:
        return filter_by_pattern(columns_head, search_str)
