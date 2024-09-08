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

from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, Field


def page_params(
    page: Annotated[int, Field(gt=0)] | None = None,
    page_size: Annotated[int, Field(gt=0)] | None = None,
) -> dict[str, int]:
    if page and page_size:
        return dict(
            offset=(page - 1) * page_size,
            limit=page_size,
        )
    return dict()


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total_count: Annotated[int, Field(ge=0)]
