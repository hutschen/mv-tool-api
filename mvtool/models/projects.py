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

from typing import Callable

from pydantic import PrivateAttr, confloat
from sqlmodel import Relationship, Session, SQLModel, func, or_, select

from .common import CommonFieldsMixin, ETagMixin
from .documents import Document
from .jira_ import JiraProject, JiraProjectImport
from .measures import Measure
from .requirements import Requirement


class AbstractProjectInput(SQLModel):
    name: str
    description: str | None


class ProjectInput(AbstractProjectInput):
    jira_project_id: str | None


class ProjectImport(ETagMixin, AbstractProjectInput):
    id: int | None = None
    jira_project: JiraProjectImport | None = None


class Project(ProjectInput, CommonFieldsMixin, table=True):
    requirements: list[Requirement] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
    )
    documents: list[Document] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
    )

    _get_jira_project: Callable = PrivateAttr()

    @property
    def jira_project(self) -> JiraProject:
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
    def completion_progress(self) -> float | None:
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
    def verification_progress(self) -> float | None:
        session = Session.object_session(self)

        # get the total number of measures in project
        total = session.execute(self._compliant_count_query).scalar()

        # get the number of verified measures in project
        verified_query = self._compliant_count_query.where(
            Measure.verification_status == "verified"
        )
        verified = session.execute(verified_query).scalar()

        return verified / total if total else None


class ProjectRepresentation(SQLModel):
    id: int
    name: str


class ProjectOutput(ProjectInput):
    id: int
    jira_project: JiraProject | None
    completion_progress: confloat(ge=0, le=1) | None
    verification_progress: confloat(ge=0, le=1) | None
