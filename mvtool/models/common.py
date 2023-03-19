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
from typing import Any

from pydantic import constr, validator
from sqlmodel import Field, SQLModel


class CommonFieldsMixin(SQLModel):
    id: int = Field(default=None, primary_key=True)
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs=dict(onupdate=datetime.utcnow),
    )


class EqualityMixin(SQLModel):
    """A mixin class for Pydantic models that adds hash and equality functionality.

    This mixin provides `__hash__` and `__eq__` methods that allow for comparing
    Pydantic models based on their field values, including nested Pydantic models. It is
    intended to be used with Pydantic models that inherit from SQLModel.

    Note: Do not use this mixin with models that have fields like `list` or `dict`
    because this mutable types are not hashable.
    """

    def __hash__(self):
        """Calculate the hash value of a Pydantic model based on its field values.

        Returns:
            int: The hash value of the model.
        """
        return hash(
            tuple(
                self.__hash_nested(getattr(self, name))
                for name in sorted(self.__fields__.keys())
            )
        )

    def __eq__(self, other: Any):
        """Compare the equality of two Pydantic models based on their field values.

        Args:
            other (Any): The object to compare with this model.

        Returns:
            bool: True if the models are instances of the same class and have equal
            field values, False otherwise.
        """
        return isinstance(other, self.__class__) and self.__hash__() == other.__hash__()

    def __hash_nested(self, value):
        """Helper method to calculate the hash value of a nested model.

        Args:
            value (Any): The field value.

        Returns:
            Any: The hash value of the field value if it is an instance of HashEqMixin,
            or the value unchanged.
        """
        if isinstance(value, EqualityMixin):
            return hash(value)
        return value


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
