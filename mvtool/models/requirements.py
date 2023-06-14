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

from typing import TYPE_CHECKING

from pydantic import BaseModel, confloat
from sqlalchemy import Column, ForeignKey, Integer, String, func, or_, select
from sqlalchemy.orm import Session, relationship

from ..db.database import Base
from .common import AbstractComplianceInput, CommonFieldsMixin, ETagMixin
from .measures import Measure

if TYPE_CHECKING:
    from .catalog_requirements import CatalogRequirementImport, CatalogRequirementOutput
    from .projects import ProjectImport, ProjectOutput


class AbstractRequirementInput(BaseModel):
    reference: str | None
    summary: str
    description: str | None


class RequirementInput(AbstractRequirementInput, AbstractComplianceInput):
    # Enable ORM mode to create requirement inputs from catalog requirements
    class Config:
        orm_mode = True

    catalog_requirement_id: int | None
    target_object: str | None
    milestone: str | None


class RequirementImport(ETagMixin, AbstractRequirementInput, AbstractComplianceInput):
    id: int | None = None
    catalog_requirement: "CatalogRequirementImport | None"
    project: "ProjectImport | None"
    target_object: str | None
    milestone: str | None


class Requirement(CommonFieldsMixin, Base):
    __tablename__ = "requirement"
    reference = Column(String, nullable=True)
    summary = Column(String, nullable=False)
    description = Column(String, nullable=True)
    compliance_status = Column(String, nullable=True)
    compliance_comment = Column(String, nullable=True)
    target_object = Column(String, nullable=True)
    milestone = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True)
    project = relationship("Project", back_populates="requirements", lazy="joined")
    catalog_requirement_id = Column(
        Integer, ForeignKey("catalog_requirement.id"), nullable=True
    )
    catalog_requirement = relationship(
        "CatalogRequirement", back_populates="requirements", lazy="joined"
    )
    measures = relationship(
        "Measure", back_populates="requirement", cascade="all,delete,delete-orphan"
    )

    @property
    def compliance_status_hint(self):
        session = Session.object_session(self)

        # get the compliance states of all measures subordinated to this requirement
        compliance_query = select([Measure.compliance_status]).where(
            Measure.requirement_id == self.id, Measure.compliance_status != None
        )
        compliance_states = session.execute(compliance_query).scalars().all()

        # compute the compliance status hint
        exists = lambda x: any(x == c in compliance_states for c in compliance_states)
        every = lambda x: all(x == c for c in compliance_states)

        if exists("C") and not (exists("PC") or exists("NC")):
            return "C"
        elif exists("PC") or (exists("C") and exists("NC")):
            return "PC"
        elif exists("NC") and not (exists("C") or exists("PC")):
            return "NC"
        elif every("N/A") and len(compliance_states) > 0:
            return "N/A"
        else:
            return None

    @property
    def _compliant_count_query(self):
        return (
            select([func.count()])
            .select_from(Measure)
            .where(
                Measure.requirement_id == self.id,
                or_(
                    Measure.compliance_status.in_(("C", "PC")),
                    Measure.compliance_status.is_(None),
                ),
            )
        )

    @property
    def completion_progress(self) -> float | None:
        if self.compliance_status not in ("C", "PC", None):
            return None

        session = Session.object_session(self)

        # get the total number of measures subordinated to this requirement
        total = session.execute(self._compliant_count_query).scalar()

        # get the number of completed measures subordinated to this requirement
        completed_query = self._compliant_count_query.where(
            Measure.completion_status == "completed"
        )
        completed = session.execute(completed_query).scalar()

        return completed / total if total else 0.0

    @property
    def verification_progress(self) -> float | None:
        if self.compliance_status not in ("C", "PC", None):
            return None

        session = Session.object_session(self)

        # get the total number of measures subordinated to this requirement
        total = session.execute(self._compliant_count_query).scalar()

        # get the number of verified measures subordinated to this requirement
        verified_query = self._compliant_count_query.where(
            Measure.verification_status == "verified"
        )
        verified = session.execute(verified_query).scalar()

        return verified / total if total else 0.0


class RequirementRepresentation(BaseModel):
    class Config:
        orm_mode = True

    id: int
    reference: str | None
    summary: str


class RequirementOutput(AbstractRequirementInput):
    class Config:
        orm_mode = True

    id: int
    project: "ProjectOutput"
    catalog_requirement: "CatalogRequirementOutput | None"
    target_object: str | None
    milestone: str | None
    compliance_status: str | None
    compliance_status_hint: str | None
    compliance_comment: str | None
    completion_progress: confloat(ge=0, le=1) | None
    verification_progress: confloat(ge=0, le=1) | None
