# coding: utf-8
#
# Copyright (C) 2022 Helmar Hutschenreuter
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

from typing import Any, Dict
from fastapi import HTTPException


class ValueHttpError(HTTPException, ValueError):
    def __init__(
        self, detail: Any = None, headers: Dict[str, Any] | None = None
    ) -> None:
        HTTPException.__init__(self, status_code=400, detail=detail, headers=headers)


class NotFoundError(HTTPException):
    def __init__(
        self, detail: Any = None, headers: Dict[str, Any] | None = None
    ) -> None:
        HTTPException.__init__(self, status_code=404, detail=detail, headers=headers)


class ClientError(HTTPException):
    def __init__(
        self, detail: Any = None, headers: Dict[str, Any] | None = None
    ) -> None:
        HTTPException.__init__(self, status_code=400, detail=detail, headers=headers)
