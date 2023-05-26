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

import pytest
from sqlalchemy import Column, String, select
from sqlalchemy.dialects import sqlite
from sqlmodel import AutoString

from mvtool.utils.filtering import filter_by_pattern, filter_by_values


@pytest.mark.parametrize(
    "pattern, negate, expected",
    [
        ("test", False, "WHERE lower(test) LIKE lower('test')"),
        ("test", True, "WHERE lower(test) NOT LIKE lower('test')"),
    ],
)
def test_filter_by_pattern(pattern, negate, expected):
    column = Column("test", AutoString)

    where_clause = filter_by_pattern(column, pattern, negate)
    select_statement = select([column]).where(where_clause)
    compiled_statement = select_statement.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )

    assert str(compiled_statement) == "SELECT test \n" + expected


@pytest.mark.parametrize(
    "values,negate,expected",
    [
        ([1], False, "WHERE test = 1"),
        ([1, 2], False, "WHERE test IN (1, 2)"),
        ([1], True, "WHERE test != 1"),
        ([1, 2], True, "WHERE (test NOT IN (1, 2))"),
    ],
)
def test_filter_by_values(values, negate, expected):
    column = Column("test", String)

    where_clause = filter_by_values(column, values, negate)
    select_statement = select([column]).where(where_clause)
    compiled_statement = select_statement.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )

    assert str(compiled_statement) == "SELECT test \n" + expected
