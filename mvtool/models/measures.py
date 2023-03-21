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


from typing import TYPE_CHECKING, Callable

from pydantic import PrivateAttr, constr, validator
from sqlmodel import Field, Relationship, SQLModel

from .common import AbstractComplianceInput, CommonFieldsMixin, ETagMixin
from .jira_ import JiraIssue, JiraIssueImport

if TYPE_CHECKING:
    from .documents import Document, DocumentOutput, DocumentImport
    from .requirements import Requirement, RequirementOutput, RequirementImport


class AbstractMeasureInput(AbstractComplianceInput):
    reference: str | None
    summary: str
    description: str | None
    completion_status: constr(regex=r"^(open|in progress|completed)$") | None
    completion_comment: str | None
    verification_method: constr(regex=r"^(I|T|R)$") | None
    verification_status: constr(
        regex=r"^(verified|partially verified|not verified)$"
    ) | None
    verification_comment: str | None

    @validator("completion_comment")
    def completion_comment_validator(cls, v, values):
        return cls._dependent_field_validator(
            "completion_comment", "completion_status", v, values
        )

    @validator("verification_status")
    def verification_status_validator(cls, v, values):
        return cls._dependent_field_validator(
            "verification_status", "verification_method", v, values
        )

    @validator("verification_comment")
    def verification_comment_validator(cls, v, values):
        return cls._dependent_field_validator(
            "verification_comment", "verification_method", v, values
        )


class MeasureInput(AbstractMeasureInput):
    document_id: int | None
    jira_issue_id: str | None


class MeasureImport(ETagMixin, AbstractMeasureInput):
    id: int | None = None
    requirement: "RequirementImport | None"
    document: "DocumentImport | None"
    jira_issue: JiraIssueImport | None


class Measure(MeasureInput, CommonFieldsMixin, table=True):
    requirement_id: int | None = Field(default=None, foreign_key="requirement.id")
    requirement: "Requirement" = Relationship(
        back_populates="measures", sa_relationship_kwargs=dict(lazy="joined")
    )
    document_id: int | None = Field(default=None, foreign_key="document.id")
    document: "Document" = Relationship(
        back_populates="measures", sa_relationship_kwargs=dict(lazy="joined")
    )

    _get_jira_issue: Callable = PrivateAttr()

    @property
    def jira_issue(self) -> JiraIssue | None:
        if self.jira_issue_id is None:
            return None

        return getattr(self, "_get_jira_issue")(self.jira_issue_id)

    @property
    def completion_status_hint(self):
        if self.compliance_status not in ("C", "PC", None):
            return None

        if self.jira_issue and self.jira_issue.status.completed:
            return "completed"
        else:
            return self.completion_status


class MeasureRepresentation(SQLModel):
    id: int
    reference: str | None
    summary: str


class MeasureOutput(MeasureRepresentation):
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
