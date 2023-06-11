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


from typing import TYPE_CHECKING

from pydantic import constr, validator
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlmodel import SQLModel

from ..database import Base
from .common import AbstractComplianceInput, CommonFieldsMixin, ETagMixin
from .jira_ import JiraIssue, JiraIssueImport

if TYPE_CHECKING:
    from .documents import DocumentImport, DocumentOutput
    from .requirements import RequirementImport, RequirementOutput


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


class Measure(CommonFieldsMixin, Base):
    __tablename__ = "measure"
    reference = Column(String, nullable=True)
    summary = Column(String, nullable=False)
    description = Column(String, nullable=True)
    compliance_status = Column(String, nullable=True)
    compliance_comment = Column(String, nullable=True)
    completion_status = Column(String, nullable=True)
    completion_comment = Column(String, nullable=True)
    verification_method = Column(String, nullable=True)
    verification_status = Column(String, nullable=True)
    verification_comment = Column(String, nullable=True)
    jira_issue_id = Column(String, nullable=True)

    requirement_id = Column(Integer, ForeignKey("requirement.id"), nullable=True)
    requirement = relationship("Requirement", back_populates="measures", lazy="joined")
    document_id = Column(Integer, ForeignKey("document.id"), nullable=True)
    document = relationship("Document", back_populates="measures", lazy="joined")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._get_jira_issue = lambda _: None

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
