# -*- coding: utf-8 -*-
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


from typing import TYPE_CHECKING, Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from .common import AbstractComplianceInput, AutoNumber, ETagMixin
from .jira_ import JiraIssue, JiraIssueImport

if TYPE_CHECKING:
    from .documents import DocumentImport, DocumentOutput
    from .requirements import RequirementImport, RequirementOutput


class AbstractMeasureInput(AbstractComplianceInput):
    reference: str | None = None
    summary: str
    description: str | None = None
    # TODO: Define custom type CompletionStatus centrally
    completion_status: (
        Annotated[str, StringConstraints(pattern=r"^(open|in progress|completed)$")]
        | None
    ) = None
    completion_comment: str | None = None
    # TODO: Define custom type VerificationMethod centrally
    verification_method: (
        Annotated[str, StringConstraints(pattern=r"^(I|T|R)$")] | None
    ) = None
    # TODO: Define custom type VerificationStatus centrally
    verification_status: (
        Annotated[
            str,
            StringConstraints(pattern=r"^(verified|partially verified|not verified)$"),
        ]
        | None
    ) = None
    verification_comment: str | None = None

    @field_validator("completion_comment")
    def completion_comment_validator(cls, v, info: ValidationInfo):
        return cls._dependent_field_validator(
            "completion_comment", "completion_status", v, info.data
        )

    @field_validator("verification_status")
    def verification_status_validator(cls, v, info: ValidationInfo):
        return cls._dependent_field_validator(
            "verification_status", "verification_method", v, info.data
        )

    @field_validator("verification_comment")
    def verification_comment_validator(cls, v, info: ValidationInfo):
        return cls._dependent_field_validator(
            "verification_comment", "verification_method", v, info.data
        )


class MeasureInput(AbstractMeasureInput):
    document_id: int | None = None
    jira_issue_id: str | None = None


class MeasurePatch(MeasureInput):
    summary: str | None = None

    @field_validator("summary")
    def summary_validator(cls, v):
        if not v:
            raise ValueError("summary must not be empty")
        return v


class MeasurePatchMany(MeasurePatch):
    reference: str | AutoNumber | None = None

    def to_patch(self, counter: int) -> MeasurePatch:
        items = self.model_dump(exclude_unset=True)
        if isinstance(self.reference, AutoNumber):
            items["reference"] = self.reference.to_value(counter)
        return MeasurePatch(**items)


class MeasureImport(ETagMixin, AbstractMeasureInput):
    id: int | None = None
    requirement: "RequirementImport | None" = None
    document: "DocumentImport | None" = None
    jira_issue: JiraIssueImport | None = None


class MeasureRepresentation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str | None
    summary: str


class MeasureOutput(MeasureRepresentation):
    model_config = ConfigDict(from_attributes=True)

    description: str | None
    compliance_status: str | None
    compliance_comment: str | None
    completion_status: str | None
    completion_status_hint: str | None
    completion_comment: str | None
    verification_status: str | None
    verification_method: str | None
    verification_comment: str | None
    requirement: "RequirementOutput"
    jira_issue_id: str | None
    jira_issue: JiraIssue | None
    document: "DocumentOutput | None"
