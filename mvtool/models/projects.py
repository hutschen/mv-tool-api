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

from pydantic import BaseModel, confloat
from sqlalchemy import Column, String, func, or_, select
from sqlalchemy.orm import Session, relationship

from ..database import Base
from .common import CommonFieldsMixin, ETagMixin
from .jira_ import JiraProject, JiraProjectImport
from .measures import Measure
from .requirements import Requirement


class AbstractProjectInput(BaseModel):
    name: str
    description: str | None


class ProjectInput(AbstractProjectInput):
    jira_project_id: str | None


class ProjectImport(ETagMixin, AbstractProjectInput):
    id: int | None = None
    jira_project: JiraProjectImport | None = None


class Project(CommonFieldsMixin, Base):
    __tablename__ = "project"
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    jira_project_id = Column(String, nullable=True)
    requirements = relationship(
        "Requirement", back_populates="project", cascade="all,delete,delete-orphan"
    )
    documents = relationship(
        "Document", back_populates="project", cascade="all,delete,delete-orphan"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        def _get_jira_project(jira_project_id):
            raise NotImplementedError("Getter for JIRA project not set")

        self._get_jira_project = _get_jira_project

    @property
    def jira_project(self):
        if self.jira_project_id is None:
            return None
        return getattr(self, "_get_jira_project")(self.jira_project_id)

    @property
    def _compliant_count_query(self):
        return (
            select([func.count()])
            .select_from(Requirement)
            .outerjoin(Measure)
            .where(
                Requirement.project_id == self.id,
                or_(
                    Requirement.compliance_status.in_(("C", "PC")),
                    Requirement.compliance_status.is_(None),
                ),
                or_(
                    Measure.compliance_status.in_(("C", "PC")),
                    Measure.compliance_status.is_(None),
                ),
            )
        )

    @property
    def completion_progress(self):
        session = Session.object_session(self)

        # get the total number of measures in project
        total = session.execute(self._compliant_count_query).scalar()

        # get the number of completed measures in project
        completed_query = self._compliant_count_query.where(
            Measure.completion_status == "completed"
        )
        completed = session.execute(completed_query).scalar()

        return completed / total if total else None

    @property
    def verification_progress(self):
        session = Session.object_session(self)

        # get the total number of measures in project
        total = session.execute(self._compliant_count_query).scalar()

        # get the number of verified measures in project
        verified_query = self._compliant_count_query.where(
            Measure.verification_status == "verified"
        )
        verified = session.execute(verified_query).scalar()

        return verified / total if total else None


class ProjectRepresentation(BaseModel):
    class Config:
        orm_mode = True

    id: int
    name: str


class ProjectOutput(ProjectInput):
    class Config:
        orm_mode = True

    id: int
    jira_project: JiraProject | None
    completion_progress: confloat(ge=0, le=1) | None
    verification_progress: confloat(ge=0, le=1) | None
