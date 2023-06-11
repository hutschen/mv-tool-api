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

from datetime import datetime
from hashlib import md5
from typing import Any

from pydantic import constr, validator
from sqlalchemy import Column, DateTime, Integer
from sqlmodel import SQLModel


class CommonFieldsMixin:
    id = Column(Integer, primary_key=True, autoincrement=True)
    created = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class ETagMixin(SQLModel):
    @property
    def etag(self) -> str:
        model_json = self.json(sort_keys=True, ensure_ascii=False).encode("utf-8")
        return md5(model_json).hexdigest()

    def __eq__(self, other: Any):
        return isinstance(other, self.__class__) and self.etag == other.etag


class AbstractComplianceInput(SQLModel):
    compliance_status: constr(regex=r"^(C|PC|NC|N/A)$") | None
    compliance_comment: str | None

    @classmethod
    def _dependent_field_validator(
        cls, dependent_fieldname, fieldname, dependent_value, values: dict
    ):
        if not values.get(fieldname, False) and dependent_value:
            raise ValueError(
                f"{dependent_fieldname} cannot be set when {fieldname} is not set"
            )
        return dependent_value

    @validator("compliance_comment")
    def compliance_comment_validator(cls, v, values):
        return cls._dependent_field_validator(
            "compliance_comment", "compliance_status", v, values
        )
