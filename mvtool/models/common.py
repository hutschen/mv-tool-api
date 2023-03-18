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

from pydantic import constr, validator
from sqlmodel import Field, SQLModel


class CommonFieldsMixin(SQLModel):
    id: int = Field(default=None, primary_key=True)
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs=dict(onupdate=datetime.utcnow),
    )


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
