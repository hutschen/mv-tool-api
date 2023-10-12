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

import json
from hashlib import md5
from typing import Any

from pydantic import BaseModel, ValidationInfo, conint, constr, field_validator


class ETagMixin(BaseModel):
    @property
    def etag(self) -> str:
        model_json = json.dumps(
            self.model_dump(),
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
        return md5(model_json).hexdigest()

    def __eq__(self, other: Any):
        return isinstance(other, self.__class__) and self.etag == other.etag


class AutoNumber(BaseModel):
    kind: constr(pattern=r"^(number)$")
    start: conint(ge=1) = 1
    step: conint(ge=1) = 1
    prefix: str | None = None
    suffix: str | None = None

    def to_value(self, counter: int) -> str:
        prefix = self.prefix or ""
        suffix = self.suffix or ""
        return f"{prefix}{counter * self.step + self.start}{suffix}"


class AbstractComplianceInput(BaseModel):
    compliance_status: constr(pattern=r"^(C|PC|NC|N/A)$") | None = None
    compliance_comment: str | None = None

    @classmethod
    def _dependent_field_validator(
        cls, dependent_fieldname, fieldname, dependent_value, values: dict
    ):
        if not values.get(fieldname, False) and dependent_value:
            raise ValueError(
                f"{dependent_fieldname} cannot be set when {fieldname} is not set"
            )
        return dependent_value

    @field_validator("compliance_comment")
    def compliance_comment_validator(cls, v, info: ValidationInfo):
        return cls._dependent_field_validator(
            "compliance_comment", "compliance_status", v, info.data
        )


class AbstractProgressCountsOutput(BaseModel):
    completion_count: int
    completed_count: int
    verification_count: int
    verified_count: int
